from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils import timezone
from terapia.constants import CONSULTA_ANTECEDENCIA_MINIMA, CONSULTA_ANTECEDENCIA_MAXIMA
from datetime import datetime
    

def validate_antecedencia(value):
    agora = timezone.now()

    if value < agora + CONSULTA_ANTECEDENCIA_MINIMA:
        raise ValidationError(
            f"A consulta deve ser agendada com, no mínimo, {CONSULTA_ANTECEDENCIA_MINIMA.total_seconds() // 60} minutos de antecedência."
        )
    elif value > agora + CONSULTA_ANTECEDENCIA_MAXIMA:
        raise ValidationError(
            f"A consulta não pode ser agendada para mais de {CONSULTA_ANTECEDENCIA_MAXIMA.days} dias no futuro."
        )


def validate_final_horario(value):
    horario = value.time()

    if horario.minute % 60 != 0:
        raise ValidationError("O horário deve terminar em :00.")


def validate_data_hora_agendada(value):
    """
    - Garante que a data e hora atenda a antecedência mínima e máxima para agendamento.
    - Garante que o final do horário seja :00.
    """
    validate_antecedencia(value)
    validate_final_horario(value)


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
            f"O valor da consulta deve ser entre R${min_value:.2f} e R${max_value:.2f}"
        )
    

def validate_intervalo_disponibilidade_datetime_range(value):
    """
    Garante que a data e hora estejam entre 00:00 de 01/07/2024 e 00:00 de 08/07/2024.
    """
    fuso_atual = timezone.get_current_timezone()
    data_hora_minima = datetime(2024, 7, 1, 0, 0, tzinfo=fuso_atual)
    data_hora_maxima = datetime(2024, 7, 8, 0, 0, tzinfo=fuso_atual)

    if not (data_hora_minima <= value <= data_hora_maxima):
        raise ValidationError(
            "A data e hora devem estar entre 00:00 de 01/07/2024 e 00:00 de 08/07/2024."
        )
