from django import forms
from django.contrib.auth import login
from django.views.generic import FormView
from django.urls import reverse_lazy
from django.contrib.auth.forms import AuthenticationForm
from usuario.models import Usuario
from terapia.models import Paciente, Psicologo
from usuario.forms import UsuarioCreationForm


class PacienteForm(forms.ModelForm):
    class Meta:
        model = Paciente
        fields = ['nome', 'cpf', 'foto']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
        usuario = super().save(commit=commit)
        Paciente.objects.create(
            usuario=usuario,
            nome=self.cleaned_data['nome'],
            cpf=self.cleaned_data['cpf']
        )
        return usuario


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
        fields = [
            'email',
            'nome_completo',
            'crp'
        ]

    def save(self, commit=True):
        usuario = super().save(commit=commit)
        Psicologo.objects.create(
            usuario=usuario,
            nome_completo=self.cleaned_data["nome_completo"],
            crp=self.cleaned_data["crp"],
        )
        return usuario


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label="E‑mail",
        widget=forms.EmailInput(attrs={'placeholder': 'seu@exemplo.com', 'autofocus': True})
    )
    password = forms.CharField(
        label="Senha",
        strip=False,
        widget=forms.PasswordInput(attrs={'placeholder': '••••••••'})
    )
