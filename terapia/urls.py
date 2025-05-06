from django.urls import path
from . import views

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('conta/login/', views.CustomLoginView.as_view(), name='login'),
    path('conta/cadastro/escolha/', views.CadastroEscolhaView.as_view(), name='cadastro_escolha'),
    path('conta/cadastro/paciente/', views.PacienteCadastroView.as_view(), name='cadastro_paciente'),
    path('conta/cadastro/psicologo/', views.PsicologoCadastroView.as_view(), name='cadastro_psicologo'),
    path('consulta/', views.ConsultaView.as_view(), name='consulta'),
    path('perfil/', views.PerfilView.as_view(), name='perfil'),
    path('pesquisa/', views.PesquisaView.as_view(), name='pesquisa'),
    path('minhas_consultas/', views.MinhasConsultasView.as_view(), name='minhas_consultas'),
]
