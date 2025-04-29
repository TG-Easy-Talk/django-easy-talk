from django import forms
from django.contrib.auth import get_user_model
from terapia.models import Paciente, Psicologo
from usuario.forms import UsuarioCreationForm


Usuario = get_user_model()


class PacienteCadastroForm(UsuarioCreationForm):
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


class PsicologoCadastroForm(UsuarioCreationForm):
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
            'nome_completo',
            'crp',
            'email',
        ]

    def save(self, commit=True):
        usuario = super().save(commit=commit)
        Psicologo.objects.create(
            usuario=usuario,
            nome_completo=self.cleaned_data["nome_completo"],
            crp=self.cleaned_data["crp"],
        )
        return usuario