from django.shortcuts import render
from django.views.generic.edit import CreateView

from .models import Paciente, Psicologo
from .forms import PacienteForm, PsicologoForm


class PacienteCreateView(CreateView):
    model = Paciente
    form_class = PacienteForm
    template_name = 'paciente_form.html'
    success_url = 'paciente_criar'

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class PsicologoCreateView(CreateView):
    model = Psicologo
    form_class = PsicologoForm
    template_name = 'psicologo_form.html'
    success_url = 'psicologo_criar'

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

def home(request):
    return render(request, 'base.html')