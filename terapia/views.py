from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.views.generic import TemplateView, FormView
from .forms import PacienteCadastroForm, PsicologoCadastroForm, EmailAuthenticationForm


class PacienteCadastroView(FormView):
    template_name = 'paciente_form.html'
    form_class = PacienteCadastroForm
    success_url = 'home'

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return super().form_valid(form)


class PsicologoCadastroView(FormView):
    template_name = 'psicologo_form.html'
    form_class = PsicologoCadastroForm
    success_url = 'home'

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return super().form_valid(form)


class CustomLoginView(LoginView):
    """
    Exibe o formulário de login e, em caso de sucesso,
    redireciona para a 'home'.
    """
    template_name = 'login.html'
    authentication_form = EmailAuthenticationForm


class HomeView(TemplateView):
    template_name = "home.html"


class CustomLoginView(LoginView):
    template_name = "conta/login.html"


class CadastroView(TemplateView):
    template_name = "conta/cadastro.html"


class ConsultaView(TemplateView):
    template_name = "consulta.html"

class PerfilView(TemplateView):
    template_name = "perfil.html"

class PesquisaView(TemplateView):
    template_name = "pesquisa.html"


class MinhasConsultasView(TemplateView):
    template_name = "minhas_consultas.html"

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