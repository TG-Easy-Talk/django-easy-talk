from django import forms
from django.forms import widgets, DateInput
from django.contrib.auth import get_user_model
from easy_talk.renderers import FormComValidacaoRenderer
from .models import Paciente, Psicologo, Especializacao, EstadoConsulta
from usuario.forms import UsuarioCreationForm


Usuario = get_user_model()


class PacienteCadastroForm(UsuarioCreationForm):
    default_renderer = FormComValidacaoRenderer

    nome = forms.CharField(
        max_length=50,
    )
    cpf = forms.CharField(
        label="CPF",
        max_length=14,
    )

    class Meta(UsuarioCreationForm.Meta):
        model = Usuario
        fields = ['cpf', 'nome', 'email'] # password1/password2 já vêm do pai

    def save(self, commit=True):
        usuario = super().save(commit=commit)
        Paciente.objects.create(
            usuario=usuario,
            nome=self.cleaned_data['nome'],
            cpf=self.cleaned_data['cpf']
        )
        return usuario


class PsicologoCadastroForm(UsuarioCreationForm):
    default_renderer = FormComValidacaoRenderer

    nome_completo = forms.CharField(
        max_length=50,
    )
    crp = forms.CharField(
        label="CRP",
        max_length=20,
    )

    class Meta(UsuarioCreationForm.Meta):
        model = Usuario
        fields = ['crp', 'nome_completo', 'email'] # password1/password2 já vêm do pai

    def save(self, commit=True):
        usuario = super().save(commit=commit)
        Psicologo.objects.create(
            usuario=usuario,
            nome_completo=self.cleaned_data["nome_completo"],
            crp=self.cleaned_data["crp"],
        )
        return usuario


class EstilizadorMixin:
    def aplicar_estilos(self):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aplicar_estilos()


class FormDeFiltrosEstilizadorMixin(EstilizadorMixin):
    def aplicar_estilos(self):
        if hasattr(self, 'fields'):
            for field in self.fields.values():
                if isinstance(field.widget, widgets.Input):
                    field.widget.attrs.update({
                        'class': 'shadow-none',
                    })

                elif isinstance(field, forms.ModelChoiceField):
                    field.empty_label = field.label


class PsicologoFiltrosForm(FormDeFiltrosEstilizadorMixin, forms.Form):
    especializacao = forms.ModelChoiceField(
        queryset=Especializacao.objects.all(),
        required=False,
        label="Especialização",
    )
    valor_minimo = forms.DecimalField(
        required=False,
        min_value=0,
        label="Mínimo",
        widget=forms.NumberInput(attrs={'placeholder': 'Mínimo'}),
    )
    valor_maximo = forms.DecimalField(
        required=False,
        min_value=0,
        label="Máximo",
        widget=forms.NumberInput(attrs={'placeholder': 'Máximo'}),
    )


class CustomDateInput(DateInput):
    input_type = 'date'


class ConsultaFiltrosForm(FormDeFiltrosEstilizadorMixin, forms.Form):
    estado = forms.ChoiceField(
        choices=[("", "Estado")] + EstadoConsulta.choices,
    )
    data_inicial = forms.DateTimeField(widget=CustomDateInput())
    data_final = forms.DateTimeField(widget=CustomDateInput())