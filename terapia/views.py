from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.views.generic import TemplateView, FormView
from django.views.generic.base import ContextMixin
from .forms import PacienteCadastroForm, PsicologoCadastroForm
from django.urls import reverse_lazy
from usuario.forms import EmailAuthenticationForm



class CadastroEscolhaView(TemplateView):
    template_name = 'conta/acesso/cadastro_escolha.html'


class CadastroView(FormView, ContextMixin):
    """
    Superclasse para as views de cadastro de Paciente e Psicólogo. Não deve ser instanciada diretamente.
    """
    template_name = 'conta/acesso/cadastro.html'
    success_url = reverse_lazy('home')

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["fluxos_alternativos"] = [
            {'url': reverse_lazy('login'), }
        ]
        return context


class PacienteCadastroView(CadastroView):
    form_class = PacienteCadastroForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["heading_form"] = "Cadastro de Paciente"
        return context


class PsicologoCadastroView(CadastroView):
    form_class = PsicologoCadastroForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["heading_form"] = "Cadastro de Psicólogo"
        return context


class CustomLoginView(LoginView, ContextMixin):
    """
    Exibe o formulário de login e, em caso de sucesso,
    redireciona para LOGIN_REDIRECT_URL.
    """
    template_name = 'conta/acesso/login.html'
    authentication_form = EmailAuthenticationForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["fluxo_url"] = reverse_lazy('cadastro_escolha')
        return context


class CadastroView(TemplateView):
    template_name = "conta/acesso/cadastro.html"


class HomeView(TemplateView):
    template_name = "home.html"


class ConsultaView(TemplateView):
    template_name = "consulta/consulta.html"

class PerfilView(TemplateView):
    template_name = "perfil/perfil.html"

class PesquisaView(TemplateView):
    template_name = "pesquisa/pesquisa.html"


class MinhasConsultasView(TemplateView):
    template_name = "minhas_consultas/minhas_consultas.html"

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