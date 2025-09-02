from django import forms
from .widgets import CustomDateTimeInput, CustomDateInput, DisponibilidadeInput
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from datetime import datetime
from decimal import Decimal
from easy_talk.renderers import (
    FormComValidacaoRenderer,
    FormDeFiltrosRenderer,
)
from .constants import CONSULTA_ANTECEDENCIA_MINIMA
from .models import (
    Paciente,
    Psicologo,
    Especializacao,
    Consulta,
    EstadoConsulta,
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


class PsicologoChangeForm(forms.ModelForm):
    default_renderer = FormComValidacaoRenderer
    template_name = "meu_perfil/componentes/form.html"

    disponibilidade = forms.JSONField(
        required=False,
    )

    class Meta:
        model = Psicologo
        fields = ["valor_consulta", "sobre_mim", "foto", "especializacoes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["sobre_mim"].widget.attrs.update({
            "placeholder": "Apresente-se para os pacientes do EasyTalk...",
            "rows": "8",
        })
        self.fields["foto"].widget = forms.FileInput()
        self.fields["especializacoes"].widget.attrs.update({"class": "h-100"})
        self.fields["disponibilidade"].widget = DisponibilidadeInput(
            disponibilidade=self.instance.disponibilidade
        )
        self.fields["sobre_mim"].widget.attrs.update({"rows": "8"})

    def clean_disponibilidade(self):
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


class AgendarConsultasForm(forms.Form):
    """
    Conecta com o frontend do calendário (campo hidden `data_hora_agendada`
    contendo uma lista JSON de datetimes ISO: ["YYYY-MM-DDTHH:MM[:SS]", ...]).
    Ao salvar, cria consultas com estado SOLICITADA, para posterior confirmação/cancelamento.
    """
    default_renderer = FormComValidacaoRenderer
    template_name = "perfil/componentes/form.html"

    data_hora_agendada = forms.JSONField()

    def __init__(self, *args, usuario, psicologo, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario
        self.psicologo = psicologo
        self.psicologo_id = getattr(psicologo, "pk", None)
        self.preco = psicologo.valor_consulta or Decimal("85.00")

    def clean_data_hora_agendada(self):
        raw = self.cleaned_data["data_hora_agendada"]
        if not isinstance(raw, list) or not raw:
            raise ValidationError("Selecione pelo menos um horário.")

        parsed = []
        tz = timezone.get_current_timezone()
        for s in raw:
            if len(s) == 16:
                s = s + ":00"
            try:
                dt_naive = datetime.fromisoformat(s)  # naive
            except Exception:
                raise ValidationError(f"Data/hora inválida: {s}")

            dt = (
                timezone.make_aware(dt_naive, tz)
                if timezone.is_naive(dt_naive)
                else dt_naive.astimezone(tz)
            )
            parsed.append(dt)

        parsed = sorted(set(parsed))

        agora = timezone.now()
        for dt in parsed:
            if dt < agora + CONSULTA_ANTECEDENCIA_MINIMA:
                raise ValidationError(
                    f"Horário inválido (no passado ou sem antecedência mínima): {dt}."
                )
            if not self.psicologo.esta_agendavel_em(dt):
                raise ValidationError(f"O psicólogo não tem disponibilidade em {dt}.")
            if self.usuario.paciente.ja_tem_consulta_em(dt):
                raise ValidationError(
                    f"Você já tem uma consulta que conflita com {dt}."
                )

        return parsed

    def save(self):
        horarios = self.cleaned_data["data_hora_agendada"]
        try:
            with transaction.atomic():
                criadas = []
                for dt in horarios:
                    c = Consulta(
                        paciente=self.usuario.paciente,
                        psicologo=self.psicologo,
                        data_hora_agendada=dt,
                        estado=EstadoConsulta.SOLICITADA,
                    )
                    c.full_clean()
                    c.save()
                    criadas.append(c)
                return criadas
        except IntegrityError:
            raise ValidationError(
                "Um ou mais horários acabaram de ser reservados por outra pessoa. "
                "Por favor, recarregue a página e tente novamente."
            )
