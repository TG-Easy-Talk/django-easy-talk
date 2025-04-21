from django.urls import path
from . import views
from .views import PacienteSignUpView, PsicologoSignUpView, login_view

urlpatterns = [
    path('', views.home, name='home'),
    path('signup/paciente/', PacienteSignUpView.as_view(), name='paciente_signup'),
    path('signup/psicologo/', PsicologoSignUpView.as_view(), name='psicologo_signup'),
    path('accounts/login/', login_view, name='login'),
]
