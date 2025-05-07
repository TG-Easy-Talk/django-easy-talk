from django import forms
from django.contrib.auth import get_user_model
from .models import Paciente, Psicologo, Especializacao
from usuario.forms import UsuarioCreationForm
from django.forms.widgets import Select


Usuario = get_user_model()


class PacienteCadastroForm(UsuarioCreationForm):
    nome = forms.CharField(
        max_length=50,
    )
    cpf = forms.CharField(
        label="CPF",
        max_length=14,
    )

    class Meta(UsuarioCreationForm.Meta):
        model = Usuario
        fields = ['email', 'nome', 'cpf'] # password1/password2 já vêm do pai

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
        max_length=50,
    )
    crp = forms.CharField(
        label="CRP",
        max_length=20,
    )

    class Meta(UsuarioCreationForm.Meta):
        model = Usuario
        fields = ['email', 'nome_completo', 'crp'] # password1/password2 já vêm do pai

    def save(self, commit=True):
        usuario = super().save(commit=commit)
        Psicologo.objects.create(
            usuario=usuario,
            nome_completo=self.cleaned_data["nome_completo"],
            crp=self.cleaned_data["crp"],
        )
        return usuario


class PsicologoFiltrosForm(forms.Form):
    especializacao = forms.ModelChoiceField(
        queryset=Especializacao.objects.all(),
        required=False,
        label="Especialização",
        widget=Select,
    )
    valor_minimo = forms.DecimalField(
        required=False,
        min_value=0,
        label="Mínimo",
    )
    valor_maximo = forms.DecimalField(
        required=False,
        min_value=0,
        label="Máximo",
    )