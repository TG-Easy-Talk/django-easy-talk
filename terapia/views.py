import json
from datetime import datetime, time, timedelta
from calendar import monthrange
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.urls import reverse_lazy
from django.views.generic import TemplateView, FormView, ListView, UpdateView
from django.views.generic.edit import ContextMixin, FormMixin, SingleObjectMixin
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.http import require_GET

from usuario.forms import EmailAuthenticationForm, UsuarioCreationForm
from .forms import (
    PacienteCreationForm,
    PsicologoCreationForm,
    PsicologoChangeForm,
    PsicologoFiltrosForm,
    ConsultaFiltrosForm,
    AgendarConsultasForm,
)
from .models import Psicologo, Consulta, EstadoConsulta, IntervaloDisponibilidade
from .widgets import DisponibilidadeInput
from .utils.disponibilidade import (
    get_disponibilidade_pela_matriz,
    get_matriz_disponibilidade_booleanos_em_javascript,
)
from .constants import CONSULTA_DURACAO_MAXIMA, CONSULTA_ANTECEDENCIA_MINIMA
from django.shortcuts import redirect, get_object_or_404
from django.views import View
from django.contrib import messages


class DeveTerCargoMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if (
            request.user.is_authenticated and
            not request.user.is_psicologo and
            not request.user.is_paciente
        ):
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


class DeveSerPsicologoMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_psicologo:
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


class FluxoAlternativoLoginContextMixin(ContextMixin):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["fluxos_alternativos"] = [
            {
                'url': reverse_lazy('login'),
                'pergunta': 'Já tem uma conta',
                'link_texto': 'Faça login',
            }
        ]
        return context


class CadastroEscolhaView(TemplateView, FluxoAlternativoLoginContextMixin):
    template_name = 'conta/cadastro_escolha.html'


class CadastroView(TemplateView, FluxoAlternativoLoginContextMixin):
    template_name = 'conta/cadastro.html'

    def get(self, request, *args, **kwargs):
        form_usuario = UsuarioCreationForm()
        form_inline = self.get_form_inline_class()()
        return self.render_to_response({
            'form': form_usuario,
            'form_inline': form_inline
        })

    def post(self, request, *args, **kwargs):
        form_usuario = UsuarioCreationForm(request.POST)
        form_inline = self.get_form_inline_class()(request.POST)
        if form_usuario.is_valid() and form_inline.is_valid():
            usuario = form_usuario.save()
            inline = form_inline.save(commit=False)
            inline.usuario = usuario
            inline.save()
                
            login(self.request, usuario)
            return self.get_redirect()

        return self.render_to_response({
            'form': form_usuario,
            'form_inline': form_inline
        })

    def get_form_inline_class(self):
        raise NotImplementedError("Subclasses devem implementar get_form_inline_class().")

    def get_redirect(self):
        raise NotImplementedError("Subclasses devem implementar get_redirect().")


class PacienteCadastroView(CadastroView):
    def get_form_inline_class(self):
        return PacienteCreationForm

    def get_redirect(self):
        return redirect('pesquisa')


class PsicologoCadastroView(CadastroView):
    def get_form_inline_class(self):
        return PsicologoCreationForm

    def get_redirect(self):
        return redirect('meu_perfil')


class CustomLoginView(LoginView):
    """
    Exibe o formulário de login e, em caso de sucesso,
    redireciona para LOGIN_REDIRECT_URL.
    """
    template_name = 'conta/login.html'
    authentication_form = EmailAuthenticationForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["fluxos_alternativos"] = [
            {
                'url': reverse_lazy('cadastro_escolha'),
                'pergunta': 'Ainda não tem uma conta',
                'link_texto': 'Cadastre-se',
            }
        ]
        return context


class HomeView(TemplateView):
    template_name = "home.html"


class ConsultaView(DeveTerCargoMixin, TemplateView):
    template_name = "consulta/consulta.html"


class PerfilView(FormView, SingleObjectMixin):
    model = Psicologo
    context_object_name = "psicologo"
    template_name = "perfil/perfil.html"
    form_class = AgendarConsultasForm
    success_url = reverse_lazy("minhas_consultas")

    def get_object(self, queryset=None):
        return Psicologo.objects.get(pk=self.kwargs["pk"])

    def _get_week_bounds(self):
        try:
            week = int(self.request.GET.get("week", "0"))
        except ValueError:
            week = 0
        week = max(0, week)

        hoje = timezone.localtime(timezone.now()).date()
        monday = hoje - timedelta(days=hoje.isoweekday() - 1)
        start = monday + timedelta(weeks=week)
        end = start + timedelta(days=6)
        return week, start, end

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario"] = self.request.user
        kwargs["psicologo"] = self.get_object()
        return kwargs

    def get_form(self, form_class=None):
        """
        Mantém compatibilidade com o widget antigo (DisponibilidadeInput)
        sem quebrar o novo formulário. Só injeta o widget se o campo existir.
        """
        form = super().get_form(form_class)
        if 'disponibilidade' in form.fields:
            week, start, end = self._get_week_bounds()
            tz = timezone.get_current_timezone()
            qs_semana = IntervaloDisponibilidade.objects.filter(
                psicologo=self.get_object(),
                data_hora_inicio__gte=datetime.combine(start, time.min, tzinfo=tz),
                data_hora_inicio__lt=datetime.combine(end + timedelta(days=1), time.min, tzinfo=tz),
            )
            form.fields['disponibilidade'].widget = DisponibilidadeInput(
                disponibilidade=qs_semana
            )
        return form

    def get_context_data(self, **kwargs):
        self.object = self.get_object()
        context = super().get_context_data(**kwargs)

        # Garante a variável usada no template: {% url 'api_agenda_slots' psicologo.id %}
        context["psicologo"] = self.object

        week, start, end = self._get_week_bounds()
        context.update({
            "week_offset": week,
            "week_start": start,
            "week_end": end,
        })

        tz = timezone.get_current_timezone()
        qs_semana = IntervaloDisponibilidade.objects.filter(
            psicologo=self.object,
            data_hora_inicio__gte=datetime.combine(start, time.min, tzinfo=tz),
            data_hora_inicio__lt=datetime.combine(end + timedelta(days=1), time.min, tzinfo=tz),
        )
        js_matriz = get_matriz_disponibilidade_booleanos_em_javascript(qs_semana)
        context["matriz_disponibilidade_booleanos"] = js_matriz
        return context

    def post(self, request, *args, **kwargs):
        if not request.user.is_paciente:
            return HttpResponseForbidden("Sua conta precisa ser do tipo paciente para agendar uma consulta.")
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        try:
            form.save()
        except ValidationError as e:
            form.add_error(None, e)
            return self.form_invalid(form)
        return super().form_valid(form)


class GetFormMixin(FormMixin):
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["data"] = self.request.GET
        return kwargs


class PesquisaView(ListView, GetFormMixin):
    template_name = "pesquisa/pesquisa.html"
    context_object_name = "psicologos"
    form_class = PsicologoFiltrosForm
    allow_empty = True

    def get_queryset(self):
        queryset = Psicologo.completos.all()

        form = self.get_form()

        if form.is_valid():
            especializacao = form.cleaned_data.get("especializacao")
            disponibilidade = form.cleaned_data.get("disponibilidade")
            valor_minimo = form.cleaned_data.get("valor_minimo")
            valor_maximo = form.cleaned_data.get("valor_maximo")

            if especializacao is not None:
                queryset = queryset.filter(especializacoes=especializacao)

            if valor_minimo is not None:
                queryset = queryset.filter(valor_consulta__gte=valor_minimo)

            if valor_maximo is not None:
                queryset = queryset.filter(valor_consulta__lte=valor_maximo)

            if disponibilidade is not None:
                psicologo_ids = [psicologo.id for psicologo in queryset.iterator() if
                                 psicologo.esta_agendavel_em(disponibilidade)]
                queryset = queryset.filter(id__in=psicologo_ids)

        return queryset


class MinhasConsultasView(DeveTerCargoMixin, ListView, GetFormMixin):
    template_name = "minhas_consultas/minhas_consultas.html"
    allow_empty = True
    context_object_name = "consultas"
    form_class = ConsultaFiltrosForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario"] = self.request.user
        return kwargs

    def get_queryset(self):
        queryset = None

        if self.request.user.is_paciente:
            queryset = Consulta.objects.filter(paciente=self.request.user.paciente)
        elif self.request.user.is_psicologo:
            queryset = Consulta.objects.filter(psicologo=self.request.user.psicologo)

        form = self.get_form()

        if form.is_valid():
            estado = form.cleaned_data.get("estado")
            paciente_ou_psicologo = form.cleaned_data.get("paciente_ou_psicologo")
            data_inicial = form.cleaned_data.get("data_inicial")
            data_final = form.cleaned_data.get("data_final")

            if estado:
                queryset = queryset.filter(estado=estado)

            if paciente_ou_psicologo is not None:
                if self.request.user.is_paciente:
                    queryset = queryset.filter(psicologo=paciente_ou_psicologo)
                else:
                    queryset = queryset.filter(paciente=paciente_ou_psicologo)

            if data_inicial is not None:
                queryset = queryset.filter(data_hora_agendada__gte=data_inicial)

            if data_final is not None:
                # Somar 1 dia para incluir até as 23:59 da data final especificada
                queryset = queryset.filter(data_hora_agendada__lt=data_final + timedelta(days=1))

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Adicionar um atributo de classes do Bootstrap
        consulta_classes_dict = {
            EstadoConsulta.SOLICITADA: "info",
            EstadoConsulta.CONFIRMADA: "success",
            EstadoConsulta.CANCELADA: "danger",
            EstadoConsulta.EM_ANDAMENTO: "warning",
            EstadoConsulta.FINALIZADA: "completed",
        }

        for consulta in context["consultas"]:
            consulta.classe = consulta_classes_dict.get(consulta.estado, "")

            if consulta.estado != EstadoConsulta.EM_ANDAMENTO:
                consulta.classe += " text-white"

        return context


class PsicologoMeuPerfilView(LoginRequiredMixin, UpdateView):
    template_name = "meu_perfil/meu_perfil.html"
    form_class = PsicologoChangeForm
    context_object_name = "psicologo"

    def get_object(self, queryset=None):
        return Psicologo.objects.get(usuario=self.request.user)

    def _get_week_bounds(self):
        """
        Retorna (offset, início_da_semana, fim_da_semana).
        """
        tz = timezone.get_current_timezone()
        hoje = timezone.localtime(timezone.now(), tz).date()
        week = int(self.request.GET.get('week', '0'))
        start = hoje - timedelta(days=hoje.isoweekday() - 1) + timedelta(weeks=week)
        end = start + timedelta(days=6)
        return week, start, end

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        week, start, end = self._get_week_bounds()

        tz = timezone.get_current_timezone()
        qs_semana = self.object.disponibilidade.filter(
            data_hora_inicio__gte=datetime.combine(start, time.min, tzinfo=tz),
            data_hora_inicio__lt=datetime.combine(end + timedelta(days=1), time.min, tzinfo=tz),
        )

        form.fields['disponibilidade'].widget = DisponibilidadeInput(
            disponibilidade=qs_semana
        )
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        week, start, end = self._get_week_bounds()
        context.update({
            'week_offset': week,
            'week_start': start,
            'week_end': end,
        })
        return context

    def form_valid(self, form):
        resp = super().form_valid(form)

        week, start, end = self._get_week_bounds()
        tz = timezone.get_current_timezone()

        IntervaloDisponibilidade.objects.filter(
            psicologo=self.object,
            data_hora_inicio__gte=datetime.combine(start, time.min, tzinfo=tz),
            data_hora_inicio__lt=datetime.combine(end + timedelta(days=1), time.min, tzinfo=tz),
        ).delete()

        matriz = json.loads(self.request.POST.get('disponibilidade', '[]'))
        novos = get_disponibilidade_pela_matriz(
            matriz,
            week_offset=week,
            propagate=True
        )

        for intervalo in novos:
            intervalo.psicologo = self.object
            intervalo.save()

        return resp


class _ConsultaDoPsicologoMixin(DeveSerPsicologoMixin):
    """
    Garante que o usuário é psicólogo e carrega a consulta que pertence a ele.
    """

    def get_consulta(self):
        return get_object_or_404(
            Consulta,
            pk=self.kwargs["pk"],
            psicologo=self.request.user.psicologo,
        )


class ConsultaConfirmarView(_ConsultaDoPsicologoMixin, View):
    """
    Confirma uma consulta que está em estado SOLICITADA.
    Aceita apenas POST por segurança (use um <form method="post"> no template).
    """

    def post(self, request, *args, **kwargs):
        consulta = self.get_consulta()
        if consulta.estado == EstadoConsulta.SOLICITADA:
            consulta.estado = EstadoConsulta.CONFIRMADA
            consulta.save(update_fields=["estado"])
            messages.success(request, "Consulta confirmada com sucesso.")
        else:
            messages.warning(request, "Esta consulta não pode ser confirmada no estado atual.")
        return redirect("minhas_consultas")


class ConsultaCancelarView(_ConsultaDoPsicologoMixin, View):
    """
    Cancela uma consulta (seja SOLICITADA ou CONFIRMADA).
    Aceita apenas POST por segurança.
    """

    def post(self, request, *args, **kwargs):
        consulta = self.get_consulta()
        if consulta.estado in (EstadoConsulta.SOLICITADA, EstadoConsulta.CONFIRMADA):
            consulta.estado = EstadoConsulta.CANCELADA
            consulta.save(update_fields=["estado"])
            messages.success(request, "Consulta cancelada.")
        else:
            messages.warning(request, "Esta consulta não pode ser cancelada no estado atual.")
        return redirect("minhas_consultas")


@require_GET
def api_agenda_slots(request, psicologo_id):
    tz = timezone.get_current_timezone()

    try:
        psicologo = Psicologo.objects.get(pk=psicologo_id)
    except Psicologo.DoesNotExist:
        return JsonResponse({"detail": "Psicólogo não encontrado."}, status=404)

    now_local = timezone.localtime(timezone.now(), tz)
    year = int(request.GET.get("year", now_local.year))
    month = int(request.GET.get("month", now_local.month))

    first_day = datetime(year, month, 1, 0, 0, tzinfo=tz)
    _, days_in_month = monthrange(year, month)
    last_day = datetime(year, month, days_in_month, 23, 59, tzinfo=tz)

    templates = IntervaloDisponibilidade.objects.filter(psicologo=psicologo).order_by("data_hora_inicio")
    if not templates.exists():
        return JsonResponse({}, safe=True)

    step = int(CONSULTA_DURACAO_MAXIMA.total_seconds() // 60)
    slots_by_date: dict[str, list[str]] = {}

    def push_slots_between(ini: datetime, fim: datetime):
        end_for_start = fim - CONSULTA_DURACAO_MAXIMA
        if end_for_start < ini:
            return
        cur = ini.replace(minute=(ini.minute // step) * step, second=0, microsecond=0)
        while cur <= end_for_start:
            if cur >= now_local + CONSULTA_ANTECEDENCIA_MINIMA and psicologo.esta_agendavel_em(cur):
                key = cur.strftime("%Y-%m-%d")
                slots_by_date.setdefault(key, []).append(cur.strftime("%H:%M"))
            cur += timedelta(minutes=step)

    for day in range(1, days_in_month + 1):
        the_date = datetime(year, month, day, 0, 0, tzinfo=tz)
        dow = the_date.isoweekday()

        for it in templates:
            s = it.data_hora_inicio.astimezone(tz)
            e = it.data_hora_fim.astimezone(tz)

            s_dow = s.isoweekday()
            e_dow = e.isoweekday()

            if s_dow == e_dow:
                if dow != s_dow:
                    continue
                ini = datetime(year, month, day, s.hour, s.minute, tzinfo=tz)
                fim = datetime(year, month, day, e.hour, e.minute, tzinfo=tz)
                push_slots_between(ini, fim)
            else:
                next_dow = (s_dow % 7) + 1

                if dow == s_dow:
                    ini = datetime(year, month, day, s.hour, s.minute, tzinfo=tz)
                    fim = datetime(year, month, day, 23, 59, tzinfo=tz)
                    push_slots_between(ini, fim)
                elif dow == next_dow:
                    ini = datetime(year, month, day, 0, 0, tzinfo=tz)
                    fim = datetime(year, month, day, e.hour, e.minute, tzinfo=tz)
                    push_slots_between(ini, fim)
                else:
                    continue

    for key in list(slots_by_date.keys()):
        slots_by_date[key] = sorted(sorted(set(slots_by_date[key])))

    response = JsonResponse(slots_by_date, safe=True)
    response["Cache-Control"] = "no-store"
    return response


@require_GET
def api_agenda_slots(request, psicologo_id):
    tz = timezone.get_current_timezone()
    try:
        psicologo = Psicologo.objects.get(pk=psicologo_id)
    except Psicologo.DoesNotExist:
        return JsonResponse({"detail": "Psicólogo não encontrado."}, status=404)

    now_local = timezone.localtime(timezone.now(), tz)
    year = int(request.GET.get("year", now_local.year))
    month = int(request.GET.get("month", now_local.month))

    first_day = datetime(year, month, 1, 0, 0, tzinfo=tz)
    _, days_in_month = monthrange(year, month)
    last_day = datetime(year, month, days_in_month, 23, 59, tzinfo=tz)

    step = int(CONSULTA_DURACAO_MAXIMA.total_seconds() // 60)
    end_limit = last_day - CONSULTA_DURACAO_MAXIMA
    cur = first_day.replace(second=0, microsecond=0)

    slots_by_date = {}
    while cur <= end_limit:
        if (cur.minute % step) == 0:
            if cur >= now_local + CONSULTA_ANTECEDENCIA_MINIMA and psicologo.esta_agendavel_em(cur):
                key = cur.strftime("%Y-%m-%d")
                slots_by_date.setdefault(key, []).append(cur.strftime("%H:%M"))
        cur += timedelta(minutes=1)

    for k in list(slots_by_date.keys()):
        slots_by_date[k] = sorted(set(slots_by_date[k]))

    resp = JsonResponse(slots_by_date, safe=True)
    resp["Cache-Control"] = "no-store"
    return resp


@require_GET
def api_available_days(request, psicologo_id):
    """
    Retorna uma lista JSON com os dias (YYYY-MM-DD) do mês pedido
    que possuem pelo menos 1 slot disponível para o psicólogo.
    Mesmo critério de geração de slots de api_agenda_slots.
    """
    tz = timezone.get_current_timezone()

    try:
        psicologo = Psicologo.objects.get(pk=psicologo_id)
    except Psicologo.DoesNotExist:
        return JsonResponse({"detail": "Psicólogo não encontrado."}, status=404)

    now_local = timezone.localtime(timezone.now(), tz)
    year = int(request.GET.get("year", now_local.year))
    month = int(request.GET.get("month", now_local.month))

    first_day = datetime(year, month, 1, 0, 0, tzinfo=tz)
    _, days_in_month = monthrange(year, month)
    last_day = datetime(year, month, days_in_month, 23, 59, tzinfo=tz)

    intervals = IntervaloDisponibilidade.objects.filter(
        psicologo=psicologo,
        data_hora_inicio__lte=last_day,
        data_hora_fim__gte=first_day,
    ).order_by("data_hora_inicio")

    step = int(CONSULTA_DURACAO_MAXIMA.total_seconds() // 60)
    days = set()

    for it in intervals:
        start = max(it.data_hora_inicio.astimezone(tz), first_day)
        end = min(it.data_hora_fim.astimezone(tz), last_day)
        end_for_start = end - CONSULTA_DURACAO_MAXIMA
        if end_for_start < start:
            continue

        cur = start.replace(minute=(start.minute // step) * step, second=0, microsecond=0)
        while cur <= end_for_start:
            if cur >= now_local + CONSULTA_ANTECEDENCIA_MINIMA and psicologo.esta_agendavel_em(cur):
                days.add(cur.strftime("%Y-%m-%d"))
            cur += timedelta(minutes=step)

    return JsonResponse(sorted(days), safe=False)


@require_GET
def api_availability_bounds(request, psicologo_id):
    tz = timezone.get_current_timezone()

    try:
        psicologo = Psicologo.objects.get(pk=psicologo_id)
    except Psicologo.DoesNotExist:
        return JsonResponse({"min": None, "max": None}, status=404)

    qs = IntervaloDisponibilidade.objects.filter(psicologo=psicologo)
    if not qs.exists():
        return JsonResponse({"min": None, "max": None})

    first = qs.order_by("data_hora_inicio").first().data_hora_inicio.astimezone(tz)
    last = qs.order_by("-data_hora_fim").first().data_hora_fim.astimezone(tz)

    now_local = timezone.localtime(timezone.now(), tz)
    min_dt = max(first, now_local + CONSULTA_ANTECEDENCIA_MINIMA)

    return JsonResponse({
        "min": min_dt.date().isoformat(),
        "max": last.date().isoformat(),
    })
