from django import forms
from django.forms import ValidationError
from django.contrib.auth import get_user_model
from easy_talk.renderers import (
    FormComValidacaoRenderer,
    FormDeFiltrosRenderer
)
from .models import Paciente, Psicologo, Especializacao, Consulta, EstadoConsulta
from usuario.forms import UsuarioCreationForm
from .utils.crp import validate_crp
from .utils.cpf import validate_cpf


Usuario = get_user_model()


class PacienteCreationForm(UsuarioCreationForm):
    default_renderer = FormComValidacaoRenderer

    nome = forms.CharField(
        max_length=50,
    )
    cpf = forms.CharField(
        label="CPF",
        max_length=14,
        validators=[validate_cpf],
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


class PsicologoCreationForm(UsuarioCreationForm):
    default_renderer = FormComValidacaoRenderer

    nome_completo = forms.CharField(
        max_length=50,
    )
    crp = forms.CharField(
        label="CRP",
        max_length=20,
        validators=[validate_crp]
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


class PsicologoFiltrosForm(forms.Form):
    default_renderer = FormDeFiltrosRenderer
    template_name = 'pesquisa/componentes/form.html'

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


class CustomDateInput(forms.DateInput):
    input_type = 'date'


class CustomDateTimeInput(forms.DateTimeInput):
    input_type = 'datetime-local'


class ConsultaFiltrosForm(forms.Form):
    default_renderer = FormDeFiltrosRenderer
    template_name = 'minhas_consultas/componentes/form.html'

    estado = forms.ChoiceField(
        choices=[("", "Estado")] + EstadoConsulta.choices,
    )
    data_inicial = forms.DateTimeField(widget=CustomDateInput())
    data_final = forms.DateTimeField(widget=CustomDateInput())
    

class PsicologoChangeForm(forms.ModelForm):
    default_renderer = FormComValidacaoRenderer
    template_name = 'meu_perfil/componentes/form.html'

    class Meta:
        model = Psicologo
        fields = ['valor_consulta', 'sobre_mim', 'foto', 'especializacoes', 'disponibilidade']


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['sobre_mim'].widget.attrs.update({
            'placeholder': 'Apresente-se para os pacientes do EasyTalk...',
        })
        self.fields['foto'].widget = forms.FileInput()


class ConsultaCreationForm(forms.ModelForm):
    default_renderer = FormComValidacaoRenderer
    template_name = 'perfil/componentes/form.html'
    
    class Meta:
        model = Consulta
        fields = ['data_hora_marcada']

    def __init__(self, *args, usuario, psicologo, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario
        self.psicologo = psicologo
        self.fields['data_hora_marcada'].widget = CustomDateTimeInput()

    def clean(self):
        cleaned_data = super().clean()
        
        if not self.usuario.is_paciente:
            raise ValidationError("Sua conta não é do tipo paciente para poder agendar uma consulta.")

        return cleaned_data

    def _post_clean(self):
        # Setar os campos de paciente e psicólogo antes da validação da model
        if not self.errors and self.instance.pk is None:
            self.instance.paciente = self.usuario.paciente
            self.instance.psicologo = self.psicologo
            super()._post_clean()
