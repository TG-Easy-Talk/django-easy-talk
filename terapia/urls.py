from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView
from .views import DisponibilidadeSemanalAPI

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('conta/login/', views.CustomLoginView.as_view(), name='login'),
    path('conta/logout/', LogoutView.as_view(), name='logout'),
    path('conta/cadastro/escolha/', views.CadastroEscolhaView.as_view(), name='cadastro_escolha'),
    path('conta/cadastro/paciente/', views.PacienteCadastroView.as_view(), name='cadastro_paciente'),
    path('conta/cadastro/psicologo/', views.PsicologoCadastroView.as_view(), name='cadastro_psicologo'),
    path('consulta/', views.ConsultaView.as_view(), name='consulta'),
    path('perfil/<int:pk>/', views.PerfilView.as_view(), name='perfil'),
    path('pesquisa/', views.PesquisaView.as_view(), name='pesquisa'),
    path('minhas_consultas/', views.MinhasConsultasView.as_view(), name='minhas_consultas'),
    path("consultas/<int:pk>/cancelar/", views.CancelarConsultaPacienteView.as_view(), name="consulta_cancelar"),
    path('meu_perfil/', views.PsicologoMeuPerfilView.as_view(), name='meu_perfil'),
    path("consultas/<int:pk>/aceitar/", views.AceitarConsultaPsicologoView.as_view(), name="consulta_aceitar"),
    path("consultas/<int:pk>/cancelar/", views.CancelarConsultaPacienteView.as_view(), name="consulta_cancelar"),
    path("meu_perfil/api/disponibilidade/", DisponibilidadeSemanalAPI.as_view(), name="api_disponibilidade_semanal"),
    path("perfil/<int:pk>/api/disponibilidade/", views.DisponibilidadePublicaAPI.as_view(), name="api_disponibilidade_publica"),
]
