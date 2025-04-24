from django.contrib import admin
from django.contrib.auth import get_user_model
from usuario.admin import UsuarioAdmin

from .models import Paciente, Psicologo, Consulta, Especializacao

Usuario = get_user_model()


class PacienteInline(admin.StackedInline):
    model = Paciente


class PsicologoInline(admin.StackedInline):
    model = Psicologo


admin.site.unregister(Usuario)


@admin.register(Usuario)
class UsuarioAdminComInlines(UsuarioAdmin):
    inlines = [PsicologoInline, PacienteInline]

@admin.register(Psicologo)
class PsicologoAdmin(admin.ModelAdmin):
    list_display = ['nome_completo', 'crp', 'valor_consulta']
    search_fields = ['nome_completo', 'crp']
    filter_horizontal = ['especializacoes']

admin.site.register(Paciente)
admin.site.register(Especializacao)
admin.site.register(Consulta)
