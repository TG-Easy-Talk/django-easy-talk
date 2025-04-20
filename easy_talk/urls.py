from django.contrib import admin
from django.urls import path
from terapia.views import PacienteCreateView, PsicologoCreateView
urlpatterns = [
    path('admin/', admin.site.urls),
    path('paciente/criar/', PacienteCreateView.as_view(), name='paciente-create'),
    path('psicologo/criar/', PsicologoCreateView.as_view(), name='psicologo-create'),
]
