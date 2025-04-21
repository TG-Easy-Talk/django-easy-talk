from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from .models import Paciente, Psicologo

User = get_user_model()


class PsicologoSignUpForm(UserCreationForm):
    email = forms.EmailField(
        label="E‑mail",
        required=True,
        widget=forms.EmailInput(attrs={
            "placeholder": "Digite seu e‑mail",
            "class": "form-control",
        }),
        help_text="Usaremos este e‑mail para futuras comunicações."
    )
    password1 = forms.CharField(
        label="Senha",
        strip=False,
        widget=forms.PasswordInput(attrs={
            "placeholder": "Escolha uma senha segura",
            "class": "form-control",
        }),
        help_text="A senha deve ter no mínimo 8 caracteres."
    )
    password2 = forms.CharField(
        label="Confirme a senha",
        strip=False,
        widget=forms.PasswordInput(attrs={
            "placeholder": "Digite a senha novamente",
            "class": "form-control",
        }),
        help_text="Confirme a senha digitada acima."
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ["email", "password1", "password2"]  # Campos exibidos no form

    def save(self, commit=True):
        # 1) Cria o objeto User
        user = super().save(commit=False)
        user.username = self.cleaned_data["email"]
        if commit:
            user.save()
            # 2) Cria imediatamente o perfil de Psicólogo
            Psicologo.objects.create(usuario=user)
        return user


class PacienteSignUpForm(UserCreationForm):
    email = forms.EmailField(
        label="E‑mail",
        required=True,
        widget=forms.EmailInput(attrs={
            "placeholder": "Digite seu e‑mail",
            "class": "form-control",
        }),
        help_text="Serão enviados comunicados e confirmações para este e‑mail."
    )
    password1 = forms.CharField(
        label="Senha",
        strip=False,
        widget=forms.PasswordInput(attrs={
            "placeholder": "Escolha uma senha forte",
            "class": "form-control",
        }),
        help_text="Use ao menos 8 caracteres."
    )
    password2 = forms.CharField(
        label="Confirme a senha",
        strip=False,
        widget=forms.PasswordInput(attrs={
            "placeholder": "Redigite sua senha",
            "class": "form-control",
        }),
        help_text="Digite a mesma senha novamente."
    )  # Garante que password1 e password2 coincidam :contentReference[oaicite:8]{index=8}

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ["email", "password1", "password2"]  # Apenas três campos no form

    def save(self, commit=True):
        # 1) Cria o User sem gravar imediatamente
        user = super().save(commit=False)  # :contentReference[oaicite:0]{index=0}
        user.username = self.cleaned_data["email"]
        if commit:
            user.save()
            # 2) Cria o perfil de Paciente atrelado ao User
            Paciente.objects.create(usuario=user)  # :contentReference[oaicite:1]{index=1}
        return user
