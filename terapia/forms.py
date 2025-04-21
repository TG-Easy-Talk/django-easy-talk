from django import forms
from .models import Paciente, Psicologo


class PacienteForm(forms.ModelForm):
    """
    Formulário para cadastro/edição de Paciente.
    """

    class Meta:
        model = Paciente
        fields = ['nome', 'cpf', 'foto']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Widgets e labels podem ser personalizados aqui se necessário
        # Exemplo: adicionar placeholder
        self.fields['cpf'].widget.attrs.update({'placeholder': '000.000.000-00'})


class PsicologoForm(forms.ModelForm):
    """
    Formulário para cadastro/edição de Psicólogo.
    """

    class Meta:
        model = Psicologo
        fields = [
            'nome_completo',
            'crp',
            'foto',
            'sobre_mim',
            'valor_consulta',
            'disponibilidade',
        ]
