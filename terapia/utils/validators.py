from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils import timezone


def validate_future_datetime(value):
    """
    Garante que o valor da data e hora seja no futuro em relação ao timezone atual.
    """
    if value < timezone.now():
        raise ValidationError("A consulta deve ser agendada para uma data futura")


def validate_duracao_range(value):
    """
    Garante que a duração esteja entre 30 e 60 minutos.
    """
    if value < 30:
        raise ValidationError("A duração da consulta é muito curta. Há um mínimo de 30 minutos")
    if value > 60:
        raise ValidationError("A duração da consulta está muito longa; o tempo máximo permitido é de 1 hora.")


def validate_estado_solicitada(value):
    """
    Garante que o estado da consulta seja sempre 'SOLICITADA' na instanciação.
    """
    from terapia.models import EstadoConsulta
    if value != EstadoConsulta.SOLICITADA:
        raise ValidationError("A consulta deve ser sempre instanciada como 'SOLICITADA'")


def validate_valor_consulta(value):
    """
    Garante que o valor da consulta esteja entre R$ 20,00 e R$ 4 999,99.
    """
    if value is None:
        return
    min_value = Decimal('20.00')
    max_value = Decimal('4999.99')
    if value < min_value or value > max_value:
        raise ValidationError(
            f"O valor da consulta deve ser entre R$ {min_value:.2f} e R$ {max_value:.2f}"
        )
