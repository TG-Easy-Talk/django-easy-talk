from django import forms
from .utils.disponibilidade import get_matriz_disponibilidade_booleanos_em_javascript
from django.utils import timezone
from datetime import timedelta


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

        # Calcula início e fim da semana
        tz = timezone.get_current_timezone()
        hoje = timezone.localtime(timezone.now(), tz).date()
        inicio = hoje - timedelta(days=hoje.isoweekday() - 1) + timedelta(weeks=week_offset)
        self.week_start = inicio
        self.week_end = inicio + timedelta(days=6)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        # Gera matriz JavaScript com a semana correta
        matriz_js = get_matriz_disponibilidade_booleanos_em_javascript(
            self.disponibilidade,
            week_offset=self.week_offset
        )
        # Injeta variáveis no contexto para template e JS
        context['widget'].update({
            'week_offset': self.week_offset,
            'week_start': self.week_start,
            'week_end': self.week_end,
            'matriz_js': matriz_js,
        })
        return context

    def format_value(self, value):
        # Retorna JSON da matriz para o input oculto
        return get_matriz_disponibilidade_booleanos_em_javascript(
            self.disponibilidade,
            week_offset=self.week_offset
        )
