from django import forms
from .constantes import MULTIPLO_CONSULTA_DURACAO_MINUTOS
from .utilidades.disponibilidade import get_matriz_disponibilidade_booleanos_em_json


class CustomDateInput(forms.DateInput):
    input_type = 'date'


class CustomDateTimeInputComStepMultiploDuracaoConsulta(forms.DateTimeInput):
    input_type = 'datetime-local'

    def __init__(self, attrs=None):
        super().__init__(attrs)
        self.attrs['step'] = f"{MULTIPLO_CONSULTA_DURACAO_MINUTOS * 60}"


class DisponibilidadeInput(forms.HiddenInput):
    template_name = 'meu_perfil/componentes/disponibilidade_widget.html'

    def __init__(self, disponibilidade=None, attrs=None):
        super().__init__(attrs)
        self.disponibilidade = disponibilidade

    def format_value(self, value):
        return get_matriz_disponibilidade_booleanos_em_json(self.disponibilidade)