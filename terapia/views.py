from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.views.generic import TemplateView, FormView, ListView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import (
    PacienteCreationForm,
    PsicologoCreationForm,
    PsicologoChangeForm,
    PsicologoFiltrosForm,
    ConsultaFiltrosForm,
    ConsultaCreationForm,
)
from django.urls import reverse_lazy
from usuario.forms import EmailAuthenticationForm
from django.views.generic.edit import ContextMixin, FormMixin, ModelFormMixin, SingleObjectMixin
from .models import Psicologo


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
    template_name = 'conta/acesso/cadastro_escolha.html'


class CadastroView(FormView, FluxoAlternativoLoginContextMixin):
    """
    Superclasse para as views de cadastro de Paciente e Psicólogo. Não deve ser instanciada diretamente.
    """
    template_name = 'conta/acesso/cadastro.html'
    success_url = reverse_lazy('home')

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return super().form_valid(form)


class PacienteCadastroView(CadastroView):
    form_class = PacienteCreationForm

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
    form_class = PsicologoCreationForm

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
    template_name = 'conta/acesso/login.html'
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


class ConsultaView(LoginRequiredMixin, TemplateView):
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
        # Setar self.object para o SingleObjectMixin funcionar
        self.object = self.get_object()
        context = super().get_context_data(**kwargs)
        context[self.context_object_name] = self.object
        return context
    
    def form_valid(self, form):
        form.save()
        return super().form_valid(form)
    

class PesquisaView(ListView, FormMixin):
    template_name = "pesquisa/pesquisa.html"
    context_object_name = "psicologos"
    form_class = PsicologoFiltrosForm

    def get_queryset(self):
        queryset = Psicologo.objects.all()
        form = self.form_class(self.request.GET)

        if form.is_valid():
            especializacao = form.cleaned_data.get("especializacao")
            valor_minimo = form.cleaned_data.get("valor_minimo")
            valor_maximo = form.cleaned_data.get("valor_maximo")

            if especializacao:
                queryset = queryset.filter(especializacoes=especializacao)

            if valor_minimo is not None:
                queryset = queryset.filter(valor_consulta__gte=valor_minimo)

            if valor_maximo is not None:
                queryset = queryset.filter(valor_consulta__lte=valor_maximo)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = self.form_class(self.request.GET)
        return context


class MinhasConsultasView(LoginRequiredMixin, TemplateView, FormMixin):
    template_name = "minhas_consultas/minhas_consultas.html"
    form_class = ConsultaFiltrosForm


    def get_context_data(self, **kwargs):
        # Esse método é para teste do template por enquanto.
        context = super().get_context_data(**kwargs)
        context["minhas_consultas"] = [
            {
                "data": "2023-10-01",
                "hora": "10:00",
                "psicologo": "Dr. João Silva",
                "status": "Confirmada",
                "class": "success",
            },
            {
                "data": "2023-10-05",
                "hora": "14:00",
                "psicologo": "Dra. Maria Oliveira",
                "status": "Em andamento",
                "class": "warning",
            },
            {
                "data": "2023-10-10",
                "hora": "16:00",
                "psicologo": "Dr. Carlos Pereira",
                "status": "Cancelada",
                "class": "danger",
            },
            {
                "data": "2023-10-15",
                "hora": "11:00",
                "psicologo": "Dra. Ana Costa",
                "status": "Solicitada",
                "class": "info",
            },
            {
                "data": "2023-10-20",
                "hora": "09:00",
                "psicologo": "Dr. Lucas Almeida",
                "status": "Concluída",
                "class": "completed",
            },
        ]
        return context


class DeveSerPsicologoMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not hasattr(request.user, "psicologo"):
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


class PsicologoMeuPerfilView(DeveSerPsicologoMixin, UpdateView):
    template_name = "meu_perfil/meu_perfil.html"
    form_class = PsicologoChangeForm
    context_object_name = "psicologo"

    def get_object(self, queryset=None):
        return Psicologo.objects.get(usuario=self.request.user)
    