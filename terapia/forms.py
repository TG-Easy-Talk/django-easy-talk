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
    )  # EmailField gera validação automática de formato de e‑mail :contentReference[oaicite:2]{index=2}
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
    )  # Confirmação de senha usando UserCreationForm.Meta.fields :contentReference[oaicite:4]{index=4}

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ["email", "password1", "password2"]  # Campos exibidos no form

    def save(self, commit=True):
        user = super().save(commit=False)  # Cria User sem salvar no banco :contentReference[oaicite:5]{index=5}
        user.username = self.cleaned_data["email"]  # Usa o e‑mail como username
        if commit:
            user.save()  # Salva o User no banco
        return user  # Não cria o perfil de Psicologo ainda


class PacienteSignUpForm(UserCreationForm):
    email = forms.EmailField(
        label="E‑mail",
        required=True,
        widget=forms.EmailInput(attrs={
            "placeholder": "Digite seu e‑mail",
            "class": "form-control",
        }),
        help_text="Serão enviados comunicados e confirmações para este e‑mail."
    )  # EmailField fornece validação de formato e atributo required :contentReference[oaicite:6]{index=6}
    password1 = forms.CharField(
        label="Senha",
        strip=False,
        widget=forms.PasswordInput(attrs={
            "placeholder": "Escolha uma senha forte",
            "class": "form-control",
        }),
        help_text="Use ao menos 8 caracteres."
    )  # PasswordInput com validação de segurança e hash automático :contentReference[oaicite:7]{index=7}
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
        user = super().save(
            commit=False)  # Gera instância de User sem salvar ainda :contentReference[oaicite:9]{index=9}
        user.username = self.cleaned_data["email"]  # E‑mail vira username
        if commit:
            user.save()  # Persiste no banco
        return user  # Perfil de Paciente será criado posteriormente
