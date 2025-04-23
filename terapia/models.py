from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError


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
        # Checar se já há psicólogo relacionado
        if hasattr(self.usuario, 'psicologo'):
            raise ValidationError("Este usuário já está relacionado a um psicólogo.")

    def __str__(self):
        return self.nome


class Psicologo(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='psicologo'
    )
    nome_completo = models.CharField("Nome Completo", max_length=50)
    crp = models.CharField("CRP", max_length=20, unique=True)
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
        null=True
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


class Especializacao(models.Model):
    titulo = models.CharField("Título", max_length=100, unique=True)
    descricao = models.TextField("Descrição")
    psicologos = models.ManyToManyField(
        Psicologo,
        related_name='especializacoes',
        blank=True,
    )

    class Meta:
        verbose_name = "Especialização"
        verbose_name_plural = "Especializações"

    def __str__(self):
        return self.titulo


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

    def __str__(self):
        return f"Consulta em {self.data_hora_marcada.strftime('%Y-%m-%d %H:%M')}"
