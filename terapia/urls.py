from django.urls import path
from .views import (
    home,
    PacienteSignupView,
    PsicologoSignupView,
    CustomLoginView,
)

urlpatterns = [
    path('', home, name='home'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('signup/paciente/', PacienteSignupView.as_view(), name='paciente_signup'),
    path('signup/psicologo/', PsicologoSignupView.as_view(), name='psicologo_signup'),
]
