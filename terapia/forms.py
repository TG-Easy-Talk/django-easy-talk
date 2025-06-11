from django import forms
from .widgets import CustomDateTimeInput, CustomDateInput, DisponibilidadeInput
from django.contrib.auth import get_user_model
from easy_talk.renderers import (
    FormComValidacaoRenderer,
    FormDeFiltrosRenderer
)
from .models import (
    Paciente,
    Psicologo,
    Especializacao,
    Consulta,
    EstadoConsulta,
    IntervaloDisponibilidade,
)
from .utils.disponibilidade import get_disponibilidade_pela_matriz

Usuario = get_user_model()


class PacienteCreationForm(forms.ModelForm):
    default_renderer = FormComValidacaoRenderer

    class Meta:
        model = Paciente
        fields = ["cpf", "nome"]


class PsicologoCreationForm(forms.ModelForm):
    default_renderer = FormComValidacaoRenderer

    class Meta:
        model = Psicologo
        fields = ["crp", "nome_completo"]


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
        choices=EstadoConsulta.choices,
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
            self.fields["paciente_ou_psicologo"].label = "Profissional"
            self.fields["paciente_ou_psicologo"].queryset = Psicologo.objects.filter(consultas__paciente=usuario.paciente).distinct()
        else:
            self.fields["paciente_ou_psicologo"].label = "Paciente"
            self.fields["paciente_ou_psicologo"].queryset = Paciente.objects.filter(consultas__psicologo=usuario.psicologo).distinct()


class PsicologoChangeForm(forms.ModelForm):
    default_renderer = FormComValidacaoRenderer
    template_name = "meu_perfil/componentes/form.html"

    disponibilidade = forms.JSONField(
        required=False,
        help_text="Preencha sua disponibilidade na grade semanal acima."
    )

    class Meta:
        model = Psicologo
        fields = ["valor_consulta", "sobre_mim", "foto", "especializacoes"]

    def __init__(self, *args, **kwargs):
        """
        Configura campos e widgets, incluindo o DisponibilidadeInput com
        um week_offset placeholder (será injetado pela view).
        """
        super().__init__(*args, **kwargs)

        self.fields["sobre_mim"].widget.attrs.update({
            "placeholder": "Apresente-se para os pacientes do EasyTalk...",
            "rows": "8",
        })

        self.fields["foto"].widget = forms.FileInput()
        self.fields["especializacoes"].widget.attrs.update({"class": "h-100"})
        self.fields["disponibilidade"].widget = DisponibilidadeInput(
            disponibilidade=self.instance.disponibilidade,
            week_offset=0
        )

    def clean_disponibilidade(self):
        """
        Retorna apenas a matriz JSON de booleanos.
        A criação e persistência de IntervaloDisponibilidade
        ocorrerão em PsicologoMeuPerfilView.form_valid().
        """
        return self.cleaned_data.get("disponibilidade")


class ConsultaCreationForm(forms.ModelForm):
    default_renderer = FormComValidacaoRenderer
    template_name = "perfil/componentes/form.html"
    disponibilidade = forms.CharField(
        widget=DisponibilidadeInput(),
        required=False
    )

    class Meta:
        model = Consulta
        fields = ["data_hora_agendada", "disponibilidade"]

    def __init__(self, *args, usuario, psicologo, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario
        self.psicologo = psicologo
        self.fields["data_hora_agendada"].widget = CustomDateTimeInput(attrs={"step": "3600"})

    def _post_clean(self):
        self.instance.paciente = self.usuario.paciente
        self.instance.psicologo = self.psicologo
        super()._post_clean()
