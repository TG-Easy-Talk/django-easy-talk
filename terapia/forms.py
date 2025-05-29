from django import forms
from .widgets import CustomDateTimeInput, CustomDateInput, DisponibilidadeInput
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
        required=False,
        queryset=Especializacao.objects.all(),
        label="Especialização",
    )
    disponibilidade = forms.DateTimeField(
        required=False,
        widget=CustomDateTimeInput(),
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


class ConsultaFiltrosForm(forms.Form):
    default_renderer = FormDeFiltrosRenderer
    template_name = 'minhas_consultas/componentes/form.html'

    estado = forms.ChoiceField(
        required=False,
        choices=[("", "Estado")] + EstadoConsulta.choices,
    )
    paciente_ou_psicologo = forms.ModelChoiceField(
        required=False,
        queryset=None,
    )
    data_inicial = forms.DateTimeField(
        required=False,
        widget=CustomDateInput(),
    )
    data_final = forms.DateTimeField(
        required=False,
        widget=CustomDateInput(),
    )

    def __init__(self, *args, usuario, **kwargs):
        super().__init__(*args, **kwargs)
        
        if usuario.is_paciente:
            self.fields['paciente_ou_psicologo'].label = "Profissional"
            self.fields['paciente_ou_psicologo'].queryset = Psicologo.objects.filter(consultas__paciente=usuario.paciente).distinct()
        else:
            self.fields['paciente_ou_psicologo'].label = "Paciente"
            self.fields['paciente_ou_psicologo'].queryset = Paciente.objects.filter(consultas__psicologo=usuario.psicologo).distinct()


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
        self.fields['disponibilidade'].widget = DisponibilidadeInput(self.instance.disponibilidade)


class ConsultaCreationForm(forms.ModelForm):
    default_renderer = FormComValidacaoRenderer
    template_name = 'perfil/componentes/form.html'
    
    class Meta:
        model = Consulta
        fields = ['data_hora_agendada']

    def __init__(self, *args, usuario, psicologo, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario
        self.psicologo = psicologo
        self.fields['data_hora_agendada'].widget = CustomDateTimeInput(attrs={"step": "3600"})

    def _post_clean(self):
        # Setar os campos de paciente e psicólogo antes da validação da model
        self.instance.paciente = self.usuario.paciente
        self.instance.psicologo = self.psicologo
        super()._post_clean()
