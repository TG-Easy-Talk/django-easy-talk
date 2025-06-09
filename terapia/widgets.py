from django import forms
from .utils.disponibilidade import get_matriz_disponibilidade_booleanos_em_javascript


class CustomDateInput(forms.DateInput):
    input_type = 'date'


class CustomDateTimeInput(forms.DateTimeInput):
    input_type = 'datetime-local'


class DisponibilidadeInput(forms.HiddenInput):
    template_name = 'meu_perfil/componentes/disponibilidade_widget.html'

    def __init__(self, disponibilidade=None, week_offset=0, attrs=None):
        super().__init__(attrs)
        self.disponibilidade = disponibilidade
        self.week_offset = week_offset

    def format_value(self, value):
        return get_matriz_disponibilidade_booleanos_em_javascript(
            self.disponibilidade, week_offset=self.week_offset
        )