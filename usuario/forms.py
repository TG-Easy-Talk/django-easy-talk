from django import forms
from django.contrib.auth.forms import ReadOnlyPasswordHashField, AuthenticationForm
from django.core.exceptions import ValidationError

from easy_talk.renderers import FormComValidacaoRenderer
from .models import Usuario

from django_password_eye.fields import PasswordEye
from django_password_eye.widgets import PasswordEyeWidget


class UsuarioCreationForm(forms.ModelForm):
    default_renderer = FormComValidacaoRenderer

    # Use PasswordEye em vez de CharField + PasswordInput
    password1 = PasswordEye(label="")
    password2 = PasswordEye(label="")

    class Meta:
        model = Usuario
        fields = ["email"]

    def clean_password2(self):
        # Checar se as senhas coincidem
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError("As senhas não coincidem")
        return password2

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.set_password(self.cleaned_data["password1"])
        if commit:
            usuario.save()
        return usuario


class UsuarioChangeForm(forms.ModelForm):
    default_renderer = FormComValidacaoRenderer
    password = ReadOnlyPasswordHashField()

    class Meta:
        model = Usuario
        fields = ["email", "password", "is_active", "is_staff", "is_superuser"]


class EmailAuthenticationForm(AuthenticationForm):
    default_renderer = FormComValidacaoRenderer
    username = forms.EmailField(label="E-mail")
    password = PasswordEye(
        label="",
        widget=PasswordEyeWidget(attrs={"placeholder": "Senha"})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Sobrescrever a mensagem padrão de login inválido
        self.error_messages["invalid_login"] = ("Por favor, informe e-mail e senha válidos.")
