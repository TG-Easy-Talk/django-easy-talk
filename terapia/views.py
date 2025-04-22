from django.contrib.auth import login
from django.shortcuts import render
from django.views.generic import FormView
from django.urls import reverse_lazy
from .forms import PacienteSignupForm, PsicologoSignupForm
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from .forms import EmailAuthenticationForm


# class PacienteCreateView(CreateView):
#     model = Paciente
#     form_class = PacienteForm
#     template_name = 'paciente_form.html'
#     success_url = 'paciente_criar'
#
#     def form_valid(self, form):
#         form.instance.user = self.request.user
#         return super().form_valid(form)
#
#
# class PsicologoCreateView(CreateView):
#     model = Psicologo
#     form_class = PsicologoForm
#     template_name = 'psicologo_form.html'
#     success_url = 'psicologo_criar'
#
#     def form_valid(self, form):
#         form.instance.user = self.request.user
#         return super().form_valid(form)

class PacienteSignupView(FormView):
    template_name = 'paciente_form.html'
    form_class = PacienteSignupForm
    success_url = reverse_lazy('home')  # quando for o momento, redireciona para a tela personalizada do paciente

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return super().form_valid(form)


class PsicologoSignupView(FormView):
    template_name = 'psicologo_form.html'
    form_class = PsicologoSignupForm
    success_url = reverse_lazy('home')  # quando for o momento, redireciona para a tela personalizada do psicólogo

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return super().form_valid(form)


class CustomLoginView(LoginView):
    """
    Exibe o formulário de login e, em caso de sucesso,
    redireciona para a 'home'.
    """
    template_name = 'registration/login.html'
    authentication_form = EmailAuthenticationForm
    redirect_authenticated_user = False
    next_page = reverse_lazy('home')


def home(request):
    return render(request, 'base.html')
