from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('pacientes/criar/', views.PacienteCreateView.as_view(), name='paciente_criar'),
    path('psicologos/criar/', views.PsicologoCreateView.as_view(), name='psicologo_criar'),
]
