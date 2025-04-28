from django.urls import path
from . import views

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('cadastro/', views.CadastroView.as_view(), name='cadastro'),
    path('consulta/', views.ConsultaView.as_view(), name='consulta'),
    path('perfil/', views.PerfilView.as_view(), name='perfil'),
    path('pesquisa/', views.PesquisaView.as_view(), name='pesquisa'),
    path('minhas_consultas/', views.MinhasConsultasView.as_view(), name='minhas_consultas'),
    path('cadastro/paciente/', views.PacienteCadastroView.as_view(), name='paciente_cadastro'),
    path('cadastro/psicologo/', views.PsicologoCadastroView.as_view(), name='psicologo_cadastro'),
]
