from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils import timezone
from terapia.constantes import (
    CONSULTA_ANTECEDENCIA_MINIMA,
    CONSULTA_ANTECEDENCIA_MAXIMA,
    MULTIPLO_CONSULTA_DURACAO_MINUTOS,
)
from datetime import datetime
from usuario.models import Usuario
    

def validate_antecedencia(value):
    agora = timezone.now()

    if value < agora + CONSULTA_ANTECEDENCIA_MINIMA:
        raise ValidationError(
            "A consulta deve ser agendada com, no mínimo, %(antecedencia)s minutos de antecedência.",
            params={'antecedencia': CONSULTA_ANTECEDENCIA_MINIMA.total_seconds() // 60},
            code='antecedencia_minima_nao_atendida',
        )
    elif value > agora + CONSULTA_ANTECEDENCIA_MAXIMA:
        raise ValidationError(
            "A consulta não pode ser agendada para mais de %(antecedencia_maxima) dias no futuro.",
            params={'antecedencia_maxima': CONSULTA_ANTECEDENCIA_MAXIMA.days},
            code='antecedencia_maxima_nao_atendida',
        )


def validate_final_horario(value):
    horario = value.time()

    if horario.minute % MULTIPLO_CONSULTA_DURACAO_MINUTOS != 0:
        raise ValidationError(
            "O horário deve ser um múltiplo de %(multiplo)s minutos.",
            params={'multiplo': MULTIPLO_CONSULTA_DURACAO_MINUTOS},
            code='final_horario_invalido',
        )


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
    min_value = Decimal("20.00")
    max_value = Decimal("4999.99")
    if value < min_value or value > max_value:
        raise ValidationError(
            "O valor da consulta deve ser entre R$%(min_value)s e R$%(max_value)s.",
            params={"min_value": min_value, "max_value": max_value},
            code="valor_consulta_invalido",
        )
    

def validate_intervalo_disponibilidade_datetime_range(value):
    """
    Garante que a data e hora estejam entre 00:00 de 01/07/2024 e 00:00 de 08/07/2024.
    """
    data_hora_minima = datetime(2024, 7, 1, 0, 0, tzinfo=value.tzinfo)
    data_hora_maxima = datetime(2024, 7, 8, 0, 0, tzinfo=value.tzinfo)

    if not (data_hora_minima <= value <= data_hora_maxima):
        raise ValidationError(
            "A data e hora devem estar entre %(data_hora_minima)s e %(data_hora_maxima)s.",
            params={
                "data_hora_minima": data_hora_minima,
                "data_hora_maxima": data_hora_maxima,
            },
            code="intervalo_disponibilidade_datetime_range_invalido",
        )
    

def validate_usuario_nao_psicologo(usuario_pk):
    """
    Garante que o usuário não esteja vinculado a um psicólogo.
    """
    usuario = Usuario.objects.get(pk=usuario_pk)
    if usuario.is_psicologo:
        raise ValidationError(
            "Este usuário já está relacionado a um psicólogo.",
            code="psicologo_ja_relacionado",
        )


def validate_usuario_nao_paciente(usuario_pk):
    """
    Garante que o usuário não esteja vinculado a um paciente.
    """
    usuario = Usuario.objects.get(pk=usuario_pk)
    if usuario.is_paciente:
        raise ValidationError(
            "Este usuário já está relacionado a um paciente.",
            code="paciente_ja_relacionado",
        )
