from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils import timezone
from terapia.constants import CONSULTA_ANTECEDENCIA_MINIMA


def validate_future_datetime(value):
    """
    Garante que o valor da data e hora seja no futuro em relação ao timezone atual.
    """
    if value < timezone.now():
        raise ValidationError("O valor deve ser uma data futura")
    

def validate_antecedencia(value):
    """
    Garante que o valor da data e hora seja no futuro em relação ao timezone atual.
    """
    if value < timezone.now() + CONSULTA_ANTECEDENCIA_MINIMA:
        raise ValidationError(
            f"A consulta deve ser agendada com, no mínimo, {CONSULTA_ANTECEDENCIA_MINIMA.total_seconds() / 60:.0f} minutos de antecedência."
        )


def validate_valor_consulta(value):
    """
    Garante que o valor da consulta esteja entre R$ 20,00 e R$ 4.999,99.
    """
    if value is None:
        return
    min_value = Decimal('20.00')
    max_value = Decimal('4999.99')
    if value < min_value or value > max_value:
        raise ValidationError(
            f"O valor da consulta deve ser entre R$ {min_value:.2f} e R$ {max_value:.2f}"
        )
