# authuser/urls.py

from django.urls import path
from .views import PacienteCreateView, PsicologoCreateView

urlpatterns = [
    path('pacientes/novo/', PacienteCreateView.as_view(), name='paciente_create'),
    path('psicologos/novo/', PsicologoCreateView.as_view(), name='psicologo_create'),
]
