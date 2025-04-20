from django.contrib import admin
from django.contrib.auth import get_user_model
from authuser.admin import UsuarioAdmin as BaseUsuarioAdmin

from .models import Paciente, Psicologo

Usuario = get_user_model()


class PacienteInline(admin.StackedInline):
    model = Paciente
    can_delete = False
    verbose_name_plural = "Perfil de Paciente"


class PsicologoInline(admin.StackedInline):
    model = Psicologo
    can_delete = False
    verbose_name_plural = "Perfil de Psicólogo"


@admin.register(Usuario)
class UsuarioAdminComInlines(BaseUsuarioAdmin):
    inlines = [PsicologoInline, PacienteInline]
