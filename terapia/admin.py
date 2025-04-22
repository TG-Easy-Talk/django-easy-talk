from django.contrib import admin
from django.contrib.auth import get_user_model
from usuario.admin import UsuarioAdmin

from .models import Paciente, Psicologo

Usuario = get_user_model()


class PacienteInline(admin.StackedInline):
    model = Paciente


class PsicologoInline(admin.StackedInline):
    model = Psicologo


admin.site.unregister(Usuario)


@admin.register(Usuario)
class UsuarioAdminComInlines(UsuarioAdmin):
    inlines = [PsicologoInline, PacienteInline]


admin.site.register(Psicologo)
admin.site.register(Paciente)
