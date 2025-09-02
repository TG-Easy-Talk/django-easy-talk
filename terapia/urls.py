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
    path('perfil/<int:pk>', views.PerfilView.as_view(), name='perfil'),
    path('pesquisa/', views.PesquisaView.as_view(), name='pesquisa'),
    path('minhas_consultas/', views.MinhasConsultasView.as_view(), name='minhas_consultas'),
    path('meu_perfil/', views.PsicologoMeuPerfilView.as_view(), name='meu_perfil'),
    path("api/psicologos/<int:psicologo_id>/agenda/slots/", views.api_agenda_slots, name="api_agenda_slots"),
    path("api/psicologos/<int:psicologo_id>/agenda/days/", views.api_available_days, name="api_available_days"),
    path("api/psicologos/<int:psicologo_id>/agenda/bounds/", views.api_availability_bounds, name="api_availability_bounds"),
]
