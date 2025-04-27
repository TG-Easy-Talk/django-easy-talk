from django.urls import path
from .views import (
    home,
    PacienteSignupView,
    PsicologoSignupView,
    CustomLoginView,
)

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('cadastro/', views.CadastroView.as_view(), name='cadastro'),
    path('consulta/', views.ConsultaView.as_view(), name='consulta'),
    path('perfil/', views.PerfilView.as_view(), name='perfil'),
    path('pesquisa/', views.PesquisaView.as_view(), name='pesquisa'),
    path('minhas_consultas/', views.MinhasConsultasView.as_view(), name='minhas_consultas'),
    path('signup/paciente/', views.PacienteSignupView.as_view(), name='paciente_signup'),
    path('signup/psicologo/', views.PsicologoSignupView.as_view(), name='psicologo_signup'),
]
