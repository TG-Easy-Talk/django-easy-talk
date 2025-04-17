from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView

from .models import Paciente, Psicologo
from .forms import PacienteForm, PsicologoForm


class PacienteCreateView(CreateView):
    model = Paciente
    form_class = PacienteForm
    template_name = 'authuser/paciente_form.html'
    success_url = reverse_lazy('paciente_list')

    def form_valid(self, form):
        # Atribui automaticamente o usuário recém‑criado ao perfil de paciente
        form.instance.user = self.request.user
        return super().form_valid(form)


class PsicologoCreateView(CreateView):
    model = Psicologo
    form_class = PsicologoForm
    template_name = 'authuser/psicologo_form.html'
    success_url = reverse_lazy('psicologo_list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)
