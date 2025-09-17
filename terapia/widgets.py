from django import forms
from .constantes import NUMERO_PERIODOS_POR_DIA


class CustomDateInput(forms.DateInput):
    input_type = 'date'


class CustomDateTimeInput(forms.DateTimeInput):
    input_type = 'datetime-local'


class DisponibilidadeInput(forms.HiddenInput):
    template_name = 'meu_perfil/componentes/disponibilidade_widget.html'

    def __init__(self, psicologo=None, attrs=None):
        super().__init__(attrs)
        self.psicologo = psicologo

    def get_context(self, name, value, attrs):
        from .views import TabelaDisponibilidadeContextMixin
        context = super().get_context(name, value, attrs)
        context_tabela = TabelaDisponibilidadeContextMixin().get_context_data()
        context.update(context_tabela)
        context["NUMERO_PERIODOS_POR_DIA"] = NUMERO_PERIODOS_POR_DIA
        context["numero_periodos_por_dia_range"] = range(NUMERO_PERIODOS_POR_DIA)
        return context


    def format_value(self, value):
        return self.psicologo.get_matriz_disponibilidade_booleanos_em_json()