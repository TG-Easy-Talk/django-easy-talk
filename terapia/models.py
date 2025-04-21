from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.core.exceptions import ObjectDoesNotExist


class Paciente(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='paciente'
    )
    nome = models.CharField("Nome", max_length=50, blank=True, default="")
    cpf = models.CharField("CPF", max_length=14, unique=True, blank=True, default="")
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
        return self.nome or f"Paciente #{self.pk}"


class Psicologo(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='psicologo'
    )
    nome_completo = models.CharField("Nome Completo", max_length=50, blank=True, default="")
    crp = models.CharField("CRP", max_length=20, unique=True, blank=True, default="")
    foto = models.ImageField("Foto", upload_to='psicologos/fotos/', blank=True, null=True)
    sobre_mim = models.TextField("Sobre Mim", blank=True, default="")
    valor_consulta = models.DecimalField(
        "Valor da Consulta", max_digits=10, decimal_places=2,
        default=0, validators=[MinValueValidator(0)]
    )
    disponibilidade = models.JSONField("Disponibilidade", default=dict, blank=True)

    class Meta:
        verbose_name = "Psicólogo"
        verbose_name_plural = "Psicólogos"

    def clean(self):
        super().clean()
        # Checar se já há paciente relacionado
        if hasattr(self.usuario, 'Psiscólogo'):
            raise ValidationError("Este usuário já está relacionado a um paciente.")

    def __str__(self):
        return self.nome_completo or f"Psicólogo #{self.pk}"
