from django import forms
from .widgets import (
    CustomDateTimeInput,
    CustomDateInput,
    DisponibilidadeInput,
)
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


class PsicologoInfoProfissionalChangeForm(forms.ModelForm):
    default_renderer = FormComValidacaoRenderer
    template_name = "meu_perfil/componentes/form_info_profissional.html"

    class Meta:
        model = Psicologo
        fields = ["valor_consulta", "sobre_mim", "especializacoes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["sobre_mim"].widget.attrs.update({
            "placeholder": "Apresente-se para os pacientes do EasyTalk...",
        })
        self.fields["especializacoes"].widget.attrs.update({"data-combobox": "multi"})
        self.fields["sobre_mim"].widget.attrs.update({"rows": "4"})

    def save(self, commit=True):
        psicologo = super().save(commit=False)

        if commit:
            psicologo.save()
            self.save_m2m()

        return psicologo
    

class PsicologoFotoDePerfilChangeForm(forms.ModelForm):
    default_renderer = FormComValidacaoRenderer
    template_name = "meu_perfil/componentes/form_foto_de_perfil.html"

    class Meta:
        model = Psicologo
        fields = ["foto"]


class PsicologoDisponibilidadeChangeForm(forms.ModelForm):
    default_renderer = FormComValidacaoRenderer
    template_name = "meu_perfil/componentes/form_disponibilidade.html"

    disponibilidade = forms.JSONField(required=False)

    class Meta:
        model = Psicologo
        fields = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["disponibilidade"].widget = DisponibilidadeInput(
            psicologo=self.instance,
        )

    def clean_disponibilidade(self):
        return IntervaloDisponibilidade.from_matriz(self.cleaned_data.get("disponibilidade"))

    def save(self, commit=True):
        psicologo = super().save(commit=False)
        disponibilidade = self.cleaned_data.get("disponibilidade", [])

        for intervalo in disponibilidade:
            intervalo.psicologo = psicologo

        IntervaloDisponibilidade.objects.filter(psicologo=psicologo).delete()
        IntervaloDisponibilidade.objects.bulk_create(disponibilidade)

        if commit:
            psicologo.save()
            self.save_m2m()

        return psicologo


class ConsultaCreationForm(forms.ModelForm):
    default_renderer = FormComValidacaoRenderer
    template_name = "perfil/componentes/form.html"
    
    class Meta:
        model = Consulta
        fields = ["data_hora_agendada"]

    def __init__(self, *args, usuario, psicologo, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario
        self.psicologo = psicologo
        self.fields["data_hora_agendada"].widget = CustomDateTimeInput()

    def _post_clean(self):
        # Setar os campos de paciente e psicólogo antes da validação da model
        self.instance.paciente = self.usuario.paciente
        self.instance.psicologo = self.psicologo
        super()._post_clean()


class ConsultaChecklistForm(forms.ModelForm):
    """Formulário mínimo para editar o campo `checklist_tarefas` da Consulta.

    Usado pelo psicólogo para salvar/atualizar o checklist referente a uma consulta.
    """
    class Meta:
        model = Consulta
        fields = ["checklist_tarefas"]
        widgets = {
            "checklist_tarefas": forms.Textarea(attrs={"rows": 8, "placeholder": "Escreva a checklist desta consulta (tarefas, recomendações, etc.)..."}),
        }


class ConsultaAnotacoesForm(forms.ModelForm):
    """Formulário mínimo para editar o campo `anotacoes` da Consulta.

    Usado pelo psicólogo para salvar/atualizar as anotações referentes a uma consulta.
    """
    class Meta:
        model = Consulta
        fields = ["anotacoes"]
        widgets = {
            "anotacoes": forms.Textarea(attrs={"rows": 10, "placeholder": "Escreva as anotações desta consulta (observações clínicas, progressos, histórico)..."}),
        }
