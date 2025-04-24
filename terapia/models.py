import datetime
import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


def validar_cpf(cpf: str) -> bool:
    """
    Valida formato e dígitos verificadores do CPF.
    Retorna True se válido, False caso contrário.
    """
    numeros = re.sub(r'\D', '', cpf)
    if len(numeros) != 11:
        return False
    if numeros == numeros[0] * 11:
        return False
    for i in range(9, 11):
        soma = sum(int(numeros[j]) * (i + 1 - j) for j in range(i))
        resto = (soma * 10) % 11
        if resto == 10:
            resto = 0
        if resto != int(numeros[i]):
            return False
    return True


def validate_crp(value):
    # Formato NN/NNNNN
    if not re.fullmatch(r"\d{2}/\d{5}", value or ""):
        raise ValidationError("Este CRP é inválido")
    # Prefixo (UF) de 01 a 28
    prefixo = int(value.split("/")[0])
    if not (1 <= prefixo <= 28):
        raise ValidationError("Este CRP é inválido")


def validate_disponibilidade_json(disp):
    """Valida estrutura de JSON de disponibilidade"""
    if disp is None:
        return
    if not isinstance(disp, list):
        raise ValidationError("O JSON de disponibilidade está em formato incorreto")
    for item in disp:
        if not isinstance(item, dict) or 'dia_semana' not in item or 'intervalos' not in item:
            raise ValidationError("O JSON de disponibilidade está em formato incorreto")
        if not isinstance(item['intervalos'], list):
            raise ValidationError("O JSON de disponibilidade está em formato incorreto")
        for intr in item['intervalos']:
            if not isinstance(intr, dict) or 'horario_inicio' not in intr or 'horario_fim' not in intr:
                raise ValidationError("O JSON de disponibilidade está em formato incorreto")


def check_psicologo_disponibilidade(psicologo, data_hora_marcada):
    """Verifica se o psicólogo está disponível no dia e horário especificados"""
    disp = psicologo.disponibilidade or []
    dia = data_hora_marcada.isoweekday()
    current_time = data_hora_marcada.time()
    for item in disp:
        if item.get('dia_semana') != dia or not isinstance(item.get('intervalos'), list):
            continue
        for intr in item['intervalos']:
            start_str = intr.get('horario_inicio')
            end_str = intr.get('horario_fim')
            if not all(isinstance(s, str) for s in (start_str, end_str)):
                continue
            try:
                start = datetime.datetime.strptime(start_str, "%H:%M").time()
                end = datetime.datetime.strptime(end_str, "%H:%M").time()
            except ValueError:
                continue
            if start <= current_time <= end:
                return True
    return False


class Paciente(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='paciente'
    )
    nome = models.CharField("Nome", max_length=50)
    cpf = models.CharField("CPF", max_length=14, unique=True)
    foto = models.ImageField("Foto", upload_to='pacientes/fotos/', blank=True, null=True)

    class Meta:
        verbose_name = "Paciente"
        verbose_name_plural = "Pacientes"

    def clean(self):
        super().clean()
        # Primeiro, verifica se o usuário já é psicólogo
        if hasattr(self.usuario, 'psicologo'):
            raise ValidationError("Este usuário já está relacionado a um psicólogo.")
        # Depois, valida o formato e dígitos do CPF
        if not validar_cpf(self.cpf):
            raise ValidationError({'cpf': 'Este CPF é inválido'})

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
        validators=[MinValueValidator(0)],
        blank=True,
        null=True
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
    data_hora_marcada = models.DateTimeField("Data e Hora Marcada")
    duracao = models.IntegerField(
        "Duração (minutos)",
        validators=[MinValueValidator(0)]
    )
    estado = models.CharField(
        "Estado",
        max_length=20,
        choices=EstadoConsulta.choices,
        default=EstadoConsulta.SOLICITADA
    )
    anotacoes = models.TextField("Anotações", blank=True)
    checklist_tarefas = models.TextField("Checklist de Tarefas", blank=True)
    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.CASCADE,
        related_name='consultas'
    )
    psicologo = models.ForeignKey(
        Psicologo,
        on_delete=models.CASCADE,
        related_name='consultas'
    )

    class Meta:
        verbose_name = "Consulta"
        verbose_name_plural = "Consultas"

    def clean(self):
        super().clean()
        now = timezone.now()
        # Valida data futura
        if self.data_hora_marcada < now:
            raise ValidationError("A consulta deve ser agendada para uma data futura")
        # Valida disponibilidade usando função auxiliar
        if not check_psicologo_disponibilidade(self.psicologo, self.data_hora_marcada):
            raise ValidationError("O psicólogo não tem disponibilidade nessa data e horário")
        # Estado inicial obrigatório
        if self.estado != EstadoConsulta.SOLICITADA:
            raise ValidationError("A consulta deve ser sempre instanciada como 'SOLICITADA'")
        # Limites de duração
        if self.duracao > 60:
            raise ValidationError("A duração da consulta está muito longa; o tempo máximo permitido é de 1 hora.")
        if self.duracao < 30:
            raise ValidationError("A duração da consulta é muito curta. Há um mínimo é de 30 minutos")
        # Conflito de horário
        qs = Consulta.objects.filter(paciente=self.paciente, data_hora_marcada=self.data_hora_marcada)
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if qs.exists():
            raise ValidationError("Você já possui uma consulta agendada nesse horário")

    def __str__(self):
        return f"Consulta em {self.data_hora_marcada.strftime('%Y-%m-%d %H:%M')}"
