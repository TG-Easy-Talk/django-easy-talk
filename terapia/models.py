import datetime
import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from terapia.utils.crp import validate_crp
from terapia.utils.cpf import validate_cpf
from terapia.utils.availability import (
    check_psicologo_disponibilidade,
    validate_disponibilidade_json
)
from terapia.utils.validators import (
    validate_future_datetime,
    validate_duracao_range,
    validate_estado_solicitada,
    validate_valor_consulta,
)


class Paciente(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='paciente'
    )
    nome = models.CharField("Nome", max_length=50)
    cpf = models.CharField("CPF", max_length=14, unique=True, validators=[validate_cpf])
    foto = models.ImageField("Foto", upload_to='pacientes/fotos/', blank=True, null=True)

    class Meta:
        verbose_name = "Paciente"
        verbose_name_plural = "Pacientes"

    def clean(self):
        super().clean()
        # Primeiro, verifica se o usuário já é psicólogo
        if hasattr(self.usuario, 'psicologo'):
            raise ValidationError("Este usuário já está relacionado a um psicólogo.")

    def __str__(self):
        return self.nome


class Especializacao(models.Model):
    titulo = models.CharField("Título", max_length=100, unique=True)
    descricao = models.TextField("Descrição")

    class Meta:
        verbose_name = "Especialização"
        verbose_name_plural = "Especializações"

    def __str__(self):
        return self.titulo


class Psicologo(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='psicologo'
    )
    nome_completo = models.CharField("Nome Completo", max_length=50)
    crp = models.CharField("CRP", max_length=20, unique=True, validators=[validate_crp])
    foto = models.ImageField("Foto", upload_to='psicologos/fotos/', blank=True, null=True)
    sobre_mim = models.TextField("Sobre Mim", blank=True)
    valor_consulta = models.DecimalField(
        "Valor da Consulta",
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[
            MinValueValidator(0),
            validate_valor_consulta,
        ],
        help_text="Entre R$ 20,00 e R$ 4 999,99",
    )
    disponibilidade = models.JSONField(
        "Disponibilidade",
        default=dict,
        blank=True,
        null=True,
        validators=[validate_disponibilidade_json]
    )
    especializacoes = models.ManyToManyField(
        Especializacao,
        related_name='psicologos',
        blank=True,
    )

    class Meta:
        verbose_name = "Psicólogo"
        verbose_name_plural = "Psicólogos"

    def clean(self):
        super().clean()
        # Checar se já há paciente relacionado
        if hasattr(self.usuario, 'paciente'):
            raise ValidationError("Este usuário já está relacionado a um paciente.")

    def __str__(self):
        return self.nome_completo


class EstadoConsulta(models.TextChoices):
    SOLICITADA = 'SOLICITADA', 'Solicitada'
    CONFIRMADA = 'CONFIRMADA', 'Confirmada'
    CANCELADA = 'CANCELADA', 'Cancelada'
    EM_ANDAMENTO = 'EM_ANDAMENTO', 'Em andamento'
    FINALIZADA = 'FINALIZADA', 'Finalizada'


class Consulta(models.Model):
    data_hora_marcada = models.DateTimeField(
        "Data e Hora Marcada",
        validators=[validate_future_datetime],
    )
    duracao = models.IntegerField(
        "Duração (minutos)",
        validators=[validate_duracao_range],
    )
    estado = models.CharField(
        "Estado",
        max_length=20,
        choices=EstadoConsulta.choices,
        default=EstadoConsulta.SOLICITADA,
        validators=[validate_estado_solicitada],
    )
    anotacoes = models.TextField("Anotações", blank=True)
    checklist_tarefas = models.TextField("Checklist de Tarefas", blank=True)
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='consultas')
    psicologo = models.ForeignKey(Psicologo, on_delete=models.CASCADE, related_name='consultas')

    class Meta:
        verbose_name = "Consulta"
        verbose_name_plural = "Consultas"

    def clean(self):
        super().clean()
        if not check_psicologo_disponibilidade(self.psicologo, self.data_hora_marcada):
            raise ValidationError("O psicólogo não tem disponibilidade nessa data e horário")

    def validate_unique(self, exclude=None):
        super().validate_unique(exclude=exclude)
        # Conflito de horário
        qs = Consulta.objects.filter(
            paciente=self.paciente,
            data_hora_marcada=self.data_hora_marcada
        ).exclude(pk=self.pk or None)
        if qs.exists():
            raise ValidationError({
                'data_hora_marcada': 'Você já possui uma consulta agendada nesse horário'
            })

    def __str__(self):
        return f"Consulta em {self.data_hora_marcada:%Y-%m-%d %H:%M'}"
