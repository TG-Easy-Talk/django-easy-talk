from django import forms
from django.contrib.auth import login
from django.views.generic import FormView
from django.urls import reverse_lazy

from usuario.models import Usuario
from terapia.models import Paciente, Psicologo
from usuario.forms import UsuarioCreationForm


class PacienteForm(forms.ModelForm):
    class Meta:
        model = Paciente
        fields = ['nome', 'cpf', 'foto']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Widgets e labels podem ser personalizados aqui se necessário
        # Exemplo: adicionar placeholder
        self.fields['cpf'].widget.attrs.update({'placeholder': '000.000.000-00'})


class PsicologoForm(forms.ModelForm):
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


class PacienteSignupForm(UsuarioCreationForm):
    """Herdamos apenas o email + senha do UsuarioCreationForm."""
    nome = forms.CharField(
        label="Nome",
        max_length=50,
        help_text="Informe seu nome completo",
        widget=forms.TextInput(attrs={'placeholder': 'Seu nome completo'}),
    )
    cpf = forms.CharField(
        label="CPF",
        max_length=14,
        help_text="Formato: 000.000.000-00",
        widget=forms.TextInput(attrs={'placeholder': '000.000.000-00'}),
    )

    class Meta(UsuarioCreationForm.Meta):
        model = Usuario
        fields = ['email', 'nome', 'cpf']  # password1/password2 já vêm do pai

    def save(self, commit=True):
        # salva o usuário
        user = super().save(commit=commit)
        # cria o perfil vazio de Paciente
        Paciente.objects.create(
            usuario=user,
            nome=self.cleaned_data['nome'],
            cpf=self.cleaned_data['cpf']
        )
        return user


class PsicologoSignupForm(UsuarioCreationForm):
    nome_completo = forms.CharField(
        label="Nome Completo",
        max_length=50,
        help_text="Informe seu nome completo",
        widget=forms.TextInput(attrs={'placeholder': 'Seu nome completo'})
    )
    crp = forms.CharField(
        label="CRP",
        max_length=20,
        help_text="Informe seu registro profissional (CRP)",
    )

    class Meta(UsuarioCreationForm.Meta):
        model = Usuario
        fields = (
            "email",
            "nome_completo",  # novo campo adicionado
            "crp"
        )

    def save(self, commit=True):
        # Primeiro cria o usuário (email + senha)
        user = super().save(commit=commit)
        # Depois cria o perfil de Psicólogo, usando nome_completo e crp
        Psicologo.objects.create(
            usuario=user,
            nome_completo=self.cleaned_data["nome_completo"],
            crp=self.cleaned_data["crp"],
        )
        return user
