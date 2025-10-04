import json
from datetime import date, datetime, timedelta

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_protect
from django.views.generic import FormView, ListView, TemplateView, UpdateView
from django.views.generic.edit import ContextMixin, FormMixin, SingleObjectMixin

from usuario.forms import EmailAuthenticationForm, UsuarioCreationForm
from .constantes import (
    CONSULTA_ANTECEDENCIA_MAXIMA,
    CONSULTA_ANTECEDENCIA_MINIMA,
    CONSULTA_DURACAO,
    CONSULTA_DURACAO_MINUTOS,
    NUMERO_PERIODOS_POR_DIA,
)
from .forms import (
    PacienteCreationForm,
    PsicologoCreationForm,
    PsicologoChangeForm,
    PsicologoFiltrosForm,
    ConsultaCreationForm,
    ConsultaFiltrosForm,
)
from .models import Consulta, EstadoConsulta, Psicologo, WeekAvailability

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
        if request.user.is_authenticated and not getattr(request.user, "is_psicologo", False):
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Sua conta precisa ser do tipo psicólogo.")
        return super().dispatch(request, *args, **kwargs)

def monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())

class GetFormMixin(FormMixin):
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["data"] = self.request.GET
        return kwargs


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


class TabelaDisponibilidadeContextMixin(ContextMixin):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["CONSULTA_DURACAO_MINUTOS"] = CONSULTA_DURACAO_MINUTOS
        return context


class CadastroEscolhaView(TemplateView, FluxoAlternativoLoginContextMixin):
    template_name = 'conta/cadastro_escolha.html'


class CadastroView(TemplateView, FluxoAlternativoLoginContextMixin):
    template_name = 'conta/cadastro.html'

    def get(self, request, *args, **kwargs):
        form_usuario = UsuarioCreationForm()
        form_inline = self.get_form_inline_class()()
        return self.render_to_response(self.get_context_data(form=form_usuario, form_inline=form_inline))

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

        return self.render_to_response(self.get_context_data(form=form_usuario, form_inline=form_inline))

    def get_form_inline(self):
        raise NotImplementedError("Subclasses devem implementar o método get_form_inline para retornar o formulário inline específico.")

    def get_redirect(self):
        raise NotImplementedError("Subclasses devem implementar o método get_redirect para retornar a URL de redirecionamento.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update({
            'form': kwargs["form"],
            'form_inline': kwargs["form_inline"],
        })

        return context


class PacienteCadastroView(CadastroView):
    def get_form_inline_class(self):
        return PacienteCreationForm

    def get_redirect(self):
        return redirect('pesquisa')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["heading_form"] = "Cadastro de Paciente"
        context["fluxos_alternativos"].append(
            {
                'url': reverse_lazy('cadastro_psicologo'),
                'pergunta': 'É psicólogo',
                'link_texto': 'Cadastre-se como profissional',
            }
        )

        return context


class PsicologoCadastroView(CadastroView):
    def get_form_inline_class(self):
        return PsicologoCreationForm

    def get_redirect(self):
        return redirect('meu_perfil')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["heading_form"] = "Cadastro de Profissional"
        context["fluxos_alternativos"].append(
            {
                'url': reverse_lazy('cadastro_paciente'),
                'pergunta': 'É paciente',
                'link_texto': 'Cadastre-se como paciente',
            }
        )
        return context


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


class CancelarConsultaPacienteView(DeveTerCargoMixin, View):
    def post(self, request, pk):
        if not (getattr(request.user, "is_paciente", False) or getattr(request.user, "is_psicologo", False)):
            return HttpResponseForbidden("Sua conta precisa ser do tipo paciente ou psicólogo.")

        if getattr(request.user, "is_paciente", False):
            consulta = get_object_or_404(Consulta, pk=pk, paciente=request.user.paciente)
        else:
            consulta = get_object_or_404(Consulta, pk=pk, psicologo=request.user.psicologo)

        if consulta.estado == EstadoConsulta.CANCELADA:
            messages.info(request, "Esta consulta já estava cancelada.")
        else:
            consulta.estado = EstadoConsulta.CANCELADA
            consulta.save(update_fields=["estado"])
            messages.success(request, "Consulta cancelada com sucesso.")

        next_url = request.POST.get("next") or reverse_lazy("minhas_consultas")
        return redirect(next_url)

class AceitarConsultaPsicologoView(View):
    def post(self, request, pk):
        if not request.user.is_psicologo:
            return HttpResponseForbidden("Sua conta precisa ser do tipo psicólogo.")

        consulta = get_object_or_404(
            Consulta,
            pk=pk,
            psicologo=request.user.psicologo
        )

        if consulta.estado == EstadoConsulta.CONFIRMADA:
            messages.info(request, "Esta consulta já estava confirmada.")
        elif consulta.estado == EstadoConsulta.CANCELADA:
            messages.warning(request, "Não é possível confirmar uma consulta já cancelada.")
        else:
            consulta.estado = EstadoConsulta.CONFIRMADA
            consulta.save(update_fields=["estado"])
            messages.success(request, "Consulta confirmada com sucesso.")

        next_url = request.POST.get("next") or reverse_lazy("minhas_consultas")
        return redirect(next_url)


class HomeView(TemplateView):
    template_name = "home.html"


class ConsultaView(DeveTerCargoMixin, TemplateView):
    template_name = "consulta/consulta.html"


class PerfilView(FormView, SingleObjectMixin, TabelaDisponibilidadeContextMixin):
    model = Psicologo
    context_object_name = "psicologo"
    template_name = "perfil/perfil.html"
    form_class = ConsultaCreationForm
    success_url = reverse_lazy("minhas_consultas")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario"] = self.request.user
        kwargs["psicologo"] = self.get_object()
        return kwargs

    def get_context_data(self, **kwargs):
        self.object = self.get_object()
        ctx = super().get_context_data(**kwargs)
        ocupados = [
            timezone.localtime(c.data_hora_agendada).strftime("%Y-%m-%dT%H:%M")
            for c in self.object.consultas.exclude(estado=EstadoConsulta.CANCELADA)
        ]
        ctx["SLOTS_OCUPADOS_JSON"] = json.dumps(ocupados)
        return ctx

    def post(self, request, *args, **kwargs):
        if not request.user.is_paciente:
            return HttpResponseForbidden("Sua conta precisa ser do tipo paciente para agendar uma consulta.")

        agends_raw = request.POST.get("agendamentos")
        if agends_raw:
            try:
                slots = json.loads(agends_raw)
                assert isinstance(slots, list)
            except Exception:
                messages.error(request, "Formato inválido dos horários selecionados.")
                return self.get(request, *args, **kwargs)

            psicologo = self.get_object()
            paciente = request.user.paciente
            tz = timezone.get_current_timezone()

            criadas, falhas = 0, []
            with transaction.atomic():
                for s in slots:
                    try:
                        dt_naive = datetime.fromisoformat(s)
                        dt = timezone.make_aware(dt_naive, tz)
                        c = Consulta(paciente=paciente, psicologo=psicologo, data_hora_agendada=dt)
                        c.full_clean()
                        c.save()
                        criadas += 1
                    except ValidationError as ve:
                        falhas.append((s, "; ".join(sum(ve.message_dict.values(), []))))
                    except Exception as e:
                        falhas.append((s, str(e)))

            if criadas:
                messages.success(request, f"{criadas} consulta(s) solicitada(s).")
            if falhas:
                for s, msg in falhas:
                    messages.warning(request, f"Não foi possível agendar {s}: {msg}")

            return redirect(self.get_success_url())

        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


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
                psicologo_ids = [psicologo.id for psicologo in queryset.iterator() if psicologo.esta_agendavel_em(disponibilidade)]
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


class PsicologoMeuPerfilView(DeveSerPsicologoMixin, UpdateView):
    template_name = "meu_perfil/meu_perfil.html"
    form_class = PsicologoChangeForm
    context_object_name = "psicologo"

    def get_object(self, queryset=None):
        return Psicologo.objects.get(usuario=self.request.user)


def _validate_matriz(matriz):
    if not isinstance(matriz, list) or len(matriz) != 7:
        return False
    for row in matriz:
        if not isinstance(row, list) or len(row) != NUMERO_PERIODOS_POR_DIA:
            return False
        if not all(isinstance(x, bool) for x in row):
            return False
    return True


def _baseline_matrix(psicologo: Psicologo):
    try:
        j = psicologo.get_matriz_disponibilidade_booleanos_em_json()
        m = json.loads(j)
        if _validate_matriz(m):
            return m
    except Exception:
        pass
    return [[False] * NUMERO_PERIODOS_POR_DIA for _ in range(7)]


def _resolve_matrix(psicologo: Psicologo, week_start: date):
    ov = WeekAvailability.objects.filter(
        psicologo=psicologo, week_start=week_start, kind=WeekAvailability.Kind.OVERRIDE
    ).first()
    if ov and _validate_matriz(ov.matriz):
        return ov.matriz, "OVERRIDE"

    an = (WeekAvailability.objects
          .filter(psicologo=psicologo,
                  kind=WeekAvailability.Kind.ANCHOR,
                  week_start__lte=week_start)
          .order_by("-week_start")
          .first())
    if an and _validate_matriz(an.matriz):
        return an.matriz, f"ANCHOR@{an.week_start.isoformat()}"

    return _baseline_matrix(psicologo), "BASELINE"


@method_decorator(csrf_protect, name="dispatch")
class DisponibilidadeSemanalAPI(View):
    """
    GET: público (paciente ou anônimo) — requer ?week=YYYY-MM-DD e ?psicologo=<id>.
         Retorna a matriz resolvida (OVERRIDE da semana, senão última ANCHOR <= semana, senão baseline).
    POST: restrito ao psicólogo dono — salva OVERRIDE/ANCHOR da semana.
    """

    @staticmethod
    def monday_of(d: date) -> date:
        return d - timedelta(days=d.weekday())

    def get(self, request, *args, **kwargs):
        week_str = request.GET.get("week")
        d = parse_date(week_str) if week_str else None
        if d is None:
            return HttpResponseBadRequest("Parâmetro 'week' inválido ou ausente (YYYY-MM-DD).")

        psicologo_id = request.GET.get("psicologo")
        if not psicologo_id:
            if request.user.is_authenticated and getattr(request.user, "is_psicologo", False):
                psicologo = request.user.psicologo
            else:
                return HttpResponseBadRequest("Informe o parâmetro 'psicologo'.")
        else:
            psicologo = get_object_or_404(Psicologo, pk=psicologo_id)

        week_start = self.monday_of(d)

        ov = WeekAvailability.objects.filter(
            psicologo=psicologo, week_start=week_start, kind=WeekAvailability.KIND_OVERRIDE
        ).first()
        if ov and _validate_matriz(ov.matriz):
            matriz = ov.matriz
        else:
            an = (WeekAvailability.objects
                  .filter(psicologo=psicologo,
                          kind=WeekAvailability.KIND_ANCHOR,
                          week_start__lte=week_start)
                  .order_by("-week_start")
                  .first())
            if an and _validate_matriz(an.matriz):
                matriz = an.matriz
            else:
                matriz = _baseline_matrix(psicologo)

        return JsonResponse({
            "week_start": str(week_start),
            "matriz": matriz,
        })

    def post(self, request, *args, **kwargs):
        if not (request.user.is_authenticated and getattr(request.user, "is_psicologo", False)):
            return HttpResponseBadRequest("Apenas psicólogos podem salvar.")

        try:
            body = json.loads(request.body.decode("utf-8"))
        except Exception:
            return HttpResponseBadRequest("JSON inválido.")

        week_str = body.get("week")
        kind = body.get("kind")
        matriz = body.get("matriz")

        d = parse_date(week_str) if week_str else None
        if d is None:
            return HttpResponseBadRequest("Campo 'week' inválido.")
        if kind not in (WeekAvailability.KIND_OVERRIDE, WeekAvailability.KIND_ANCHOR):
            return HttpResponseBadRequest("Campo 'kind' inválido.")
        if not _validate_matriz(matriz):
            return HttpResponseBadRequest("Campo 'matriz' precisa ser 7 x NUMERO_PERIODOS_POR_DIA de booleanos.")

        week_start = self.monday_of(d)
        psicologo = request.user.psicologo

        obj, _ = WeekAvailability.objects.update_or_create(
            psicologo=psicologo,
            week_start=week_start,
            defaults={"kind": kind, "matriz": matriz},
        )

        return JsonResponse({
            "ok": True,
            "week_start": str(obj.week_start),
            "kind": obj.kind,
        })


class DisponibilidadeSemanalPublicAPI(View):
    """
    Retorna a matriz 7 x NUMERO_PERIODOS_POR_DIA para a semana pedida,
    resolvendo OVERRIDE > ANCHOR > baseline (IntervaloDisponibilidade).
    Pode ser chamada por pacientes (GET apenas).
    """
    def get(self, request, pk, *args, **kwargs):
        week_str = request.GET.get("week")
        d = parse_date(week_str) if week_str else None
        if d is None:
            return HttpResponseBadRequest("Parâmetro 'week' inválido (YYYY-MM-DD).")

        week_start = monday_of(d)
        psicologo = get_object_or_404(Psicologo, pk=pk)

        matriz, source = _resolve_matrix(psicologo, week_start)
        return JsonResponse({
            "week_start": str(week_start),
            "matriz": matriz,
            "source": source,
        })

def _validate_matriz(matriz):
    if not isinstance(matriz, list) or len(matriz) != 7:
        return False
    for row in matriz:
        if not isinstance(row, list) or len(row) != NUMERO_PERIODOS_POR_DIA:
            return False
        if not all(isinstance(x, bool) for x in row):
            return False
    return True

def _baseline_matrix(psicologo: Psicologo):
    try:
        j = psicologo.get_matriz_disponibilidade_booleanos_em_json()
        m = json.loads(j)
        if _validate_matriz(m):
            return m
    except Exception:
        pass
    return [[False] * NUMERO_PERIODOS_POR_DIA for _ in range(7)]

def _resolve_matrix(psicologo: Psicologo, week_start: date):
    """Resolve a matriz 7xN para a semana pedida, usando OVERRIDE > ANCHOR > baseline."""
    ov = WeekAvailability.objects.filter(
        psicologo=psicologo,
        week_start=week_start,
        kind=WeekAvailability.KIND_OVERRIDE,
    ).first()
    if ov and _validate_matriz(ov.matriz):
        return ov.matriz, "OVERRIDE"

    an = (WeekAvailability.objects
          .filter(psicologo=psicologo,
                  kind=WeekAvailability.KIND_ANCHOR,
                  week_start__lte=week_start)
          .order_by("-week_start")
          .first())
    if an and _validate_matriz(an.matriz):
        return an.matriz, f"ANCHOR@{an.week_start.isoformat()}"

    return _baseline_matrix(psicologo), "BASELINE"

def monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())

class DisponibilidadePublicaAPI(View):
    """
    GET /perfil/<pk>/api/disponibilidade/?week=YYYY-MM-DD
    Retorna {"week_start": "YYYY-MM-DD", "matriz": [...], "source": "..."} para o psicólogo <pk>.
    """
    def get(self, request, pk, *args, **kwargs):
        week_str = request.GET.get("week")
        d = parse_date(week_str) if week_str else None
        if d is None:
            return HttpResponseBadRequest("Parâmetro 'week' inválido ou ausente (YYYY-MM-DD).")

        week_start = monday_of(d)
        psicologo = get_object_or_404(Psicologo, pk=pk)

        matriz, source = _resolve_matrix(psicologo, week_start)
        return JsonResponse({
            "week_start": str(week_start),
            "matriz": matriz,
            "source": source,
        })