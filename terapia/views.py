# django-easy-talk/terapia/views.py

import json
from datetime import datetime, time, timedelta

from django.utils import timezone
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import TemplateView, FormView, ListView, UpdateView
from django.views.generic.edit import ContextMixin, FormMixin, SingleObjectMixin
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseForbidden

from usuario.forms import EmailAuthenticationForm, UsuarioCreationForm
from .forms import (
    PacienteCreationForm,
    PsicologoCreationForm,
    PsicologoChangeForm,
    PsicologoFiltrosForm,
    ConsultaCreationForm,
    ConsultaFiltrosForm,
)
from .models import Psicologo, Consulta, EstadoConsulta
from terapia.utils.disponibilidade import get_disponibilidade_pela_matriz
from .widgets import DisponibilidadeInput


# --- Mixins e classes de cadastro ---

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


# --- Login e home ---

class CustomLoginView(LoginView):
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


# --- Consulta e perfil público ---

class ConsultaView(DeveTerCargoMixin, TemplateView):
    template_name = "consulta/consulta.html"


class PerfilView(FormView, SingleObjectMixin):
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
        context = super().get_context_data(**kwargs)
        context[self.context_object_name] = self.object
        return context

    def post(self, request, *args, **kwargs):
        if not request.user.is_paciente:
            return HttpResponseForbidden(
                "Sua conta precisa ser do tipo paciente para agendar uma consulta."
            )
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


# --- Pesquisa e lista de consultas ---

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
            esp = form.cleaned_data.get("especializacao")
            disp = form.cleaned_data.get("disponibilidade")
            vmin = form.cleaned_data.get("valor_minimo")
            vmax = form.cleaned_data.get("valor_maximo")
            if esp is not None:
                queryset = queryset.filter(especializacoes=esp)
            if vmin is not None:
                queryset = queryset.filter(valor_consulta__gte=vmin)
            if vmax is not None:
                queryset = queryset.filter(valor_consulta__lte=vmax)
            if disp is not None:
                ids = [p.id for p in queryset if p.esta_agendavel_em(disp)]
                queryset = queryset.filter(id__in=ids)
        return queryset


class MinhasConsultasView(DeveTerCargoMixin, ListView, GetFormMixin):
    template_name = "minhas_consultas/minhas_consultas.html"
    context_object_name = "consultas"
    form_class = ConsultaFiltrosForm
    allow_empty = True

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario"] = self.request.user
        return kwargs

    def get_queryset(self):
        if self.request.user.is_paciente:
            qs = Consulta.objects.filter(paciente=self.request.user.paciente)
        else:
            qs = Consulta.objects.filter(psicologo=self.request.user.psicologo)
        form = self.get_form()
        if form.is_valid():
            estado = form.cleaned_data.get("estado")
            u = form.cleaned_data.get("paciente_ou_psicologo")
            di = form.cleaned_data.get("data_inicial")
            df = form.cleaned_data.get("data_final")
            if estado:
                qs = qs.filter(estado=estado)
            if u is not None:
                qs = qs.filter(psicologo=u) if self.request.user.is_paciente else qs.filter(paciente=u)
            if di is not None:
                qs = qs.filter(data_hora_agendada__gte=di)
            if df is not None:
                qs = qs.filter(data_hora_agendada__lte=df + timedelta(days=1))
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        classes = {
            EstadoConsulta.SOLICITADA: "info",
            EstadoConsulta.CONFIRMADA: "success",
            EstadoConsulta.CANCELADA: "danger",
            EstadoConsulta.EM_ANDAMENTO: "warning",
            EstadoConsulta.FINALIZADA: "completed",
        }
        for c in context["consultas"]:
            c.classe = classes.get(c.estado, "")
            if c.estado != EstadoConsulta.EM_ANDAMENTO:
                c.classe += " text-white"
        return context


# --- Perfil do psicólogo (edição) ---

class PsicologoMeuPerfilView(LoginRequiredMixin, UpdateView):
    template_name = "meu_perfil/meu_perfil.html"
    form_class = PsicologoChangeForm
    context_object_name = "psicologo"

    def get_object(self, queryset=None):
        return Psicologo.objects.get(usuario=self.request.user)

    def get_form(self, form_class=None):
        """
        Sobrescreve o form para injetar o widget com week_offset correto.
        """
        form = super().get_form(form_class)

        # lê o offset da URL (?week=...)
        week = int(self.request.GET.get('week', '0'))

        # usa o related_name 'disponibilidade' para pegar os IntervaloDisponibilidade
        dispo_qs = self.object.disponibilidade.all()

        # recria o widget para refletir a semana correta
        form.fields['disponibilidade'].widget = DisponibilidadeInput(
            disponibilidade=dispo_qs,
            week_offset=week
        )
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        week = int(self.request.GET.get('week', '0'))
        tz = timezone.get_current_timezone()
        hoje = timezone.localtime(timezone.now(), tz).date()
        inicio_semana = hoje - timedelta(days=hoje.isoweekday() - 1) + timedelta(weeks=week)
        fim_semana = inicio_semana + timedelta(days=6)
        context.update({
            'week_offset': week,
            'week_start': inicio_semana,
            'week_end': fim_semana,
        })
        return context

    def form_valid(self, form):
        resp = super().form_valid(form)
        matriz = json.loads(self.request.POST.get('disponibilidade', '[]'))
        week_str = self.request.POST.get('week_offset') or '0'
        week = int(week_str)
        from terapia.models import IntervaloDisponibilidade
        tz = timezone.get_current_timezone()
        hoje = timezone.localtime(timezone.now(), tz).date()
        inicio_semana = hoje - timedelta(days=hoje.isoweekday() - 1) + timedelta(weeks=week)
        IntervaloDisponibilidade.objects.filter(
            psicologo=self.object,
            data_hora_inicio__gte=datetime.combine(inicio_semana, time.min, tzinfo=tz)
        ).delete()
        novos = get_disponibilidade_pela_matriz(matriz, week)
        for intervalo in novos:
            intervalo.psicologo = self.object
            intervalo.save()
        return resp
