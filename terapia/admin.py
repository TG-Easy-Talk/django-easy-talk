from django.contrib import admin
from django.contrib.auth import get_user_model
from usuario.admin import UsuarioAdmin

from .models import Paciente, Psicologo, Consulta, Especializacao, IntervaloDisponibilidade

Usuario = get_user_model()


class PacienteInline(admin.StackedInline):
    model = Paciente


class PsicologoInline(admin.StackedInline):
    model = Psicologo


@admin.register(Usuario)
class UsuarioAdminComInlines(UsuarioAdmin):
    inlines = [PsicologoInline, PacienteInline]


@admin.register(Psicologo)
class PsicologoAdmin(admin.ModelAdmin):
    list_display = ['nome_completo', 'crp', 'valor_consulta', 'usuario', 'esta_com_perfil_completo']
    search_fields = ['nome_completo', 'crp']
    filter_horizontal = ['especializacoes']


@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = ['nome', 'cpf', 'usuario']
    search_fields = ['nome', 'cpf']


@admin.register(Especializacao)
class EspecializacaoAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'descricao']
    search_fields = ['titulo']


@admin.register(Consulta)
class ConsultaAdmin(admin.ModelAdmin):
    list_display = ['data_hora_agendada', 'estado', 'paciente', 'psicologo', 'data_hora_solicitada']
    search_fields = ['paciente__nome', 'psicologo__nome_completo']
    list_filter = ['estado', 'data_hora_agendada']


@admin.register(IntervaloDisponibilidade)
class IntervaloDisponibilidadeAdmin(admin.ModelAdmin):
    pass
