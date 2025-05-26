from django import forms
from django.core.exceptions import ValidationError
from .utils.availability import validate_disponibilidade
import json


class CustomDateInput(forms.DateInput):
    input_type = 'date'


class CustomDateTimeInput(forms.DateTimeInput):
    input_type = 'datetime-local'


class DisponibilidadeInput(forms.HiddenInput):
    template_name = 'meu_perfil/componentes/disponibilidade_widget.html'

    def __init__(self, disponibilidade=list, attrs=None):
        super().__init__(attrs)
        self.disponibilidade = disponibilidade

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        
        try:
            validate_disponibilidade(json.loads(context['widget']['value']))
        except (ValidationError, json.JSONDecodeError):
            context['widget']['value'] = self.disponibilidade

        return context