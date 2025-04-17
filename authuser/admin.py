from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model

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
class UsuarioAdmin(BaseUserAdmin):
    inlines = [PacienteInline, PsicologoInline]
    list_display = ('email', 'nome', 'sobrenome', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active')
    ordering = ('email',)
