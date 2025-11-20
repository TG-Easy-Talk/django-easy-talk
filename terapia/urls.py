from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView

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
    path('meu-perfil/informacoes-profissionais/', views.PsicologoInfoProfissionalView.as_view(), name='meu_perfil_info_profissional'),
    path('meu-perfil/foto-de-perfil/', views.PsicologoFotoDePerfilView.as_view(), name='meu_perfil_foto'),
    path('meu-perfil/disponibilidade/', views.PsicologoDisponibilidadeView.as_view(), name='meu_perfil_disponibilidade'),
    path('meu-perfil/disponibilidade/editar/', views.PsicologoEditarDisponibilidadeView.as_view(), name='meu_perfil_disponibilidade_editar'),
    path("consultas/<int:pk>/aceitar/", views.AceitarConsultaPsicologoView.as_view(), name="consulta_aceitar"),
    path("consultas/<int:pk>/checklist/", views.ConsultaChecklistUpdateView.as_view(), name="consulta_checklist"),
    path("consultas/<int:pk>/anotacoes/", views.ConsultaAnotacoesUpdateView.as_view(), name="consulta_anotacoes"),
    path("consultas/<int:pk>/cancelar/", views.CancelarConsultaPacienteView.as_view(), name="consulta_cancelar"),
]
