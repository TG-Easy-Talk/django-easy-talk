from django.urls import path
from .views import home, PacienteSignupView, PsicologoSignupView

urlpatterns = [
    path('', home, name='home'),  # rota “home”
    path('signup/paciente/', PacienteSignupView.as_view(), name='paciente_signup'),
    path('signup/psicologo/', PsicologoSignupView.as_view(), name='psicologo_signup'),
]