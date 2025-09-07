from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils import timezone
from terapia.constantes import (
    CONSULTA_ANTECEDENCIA_MINIMA,
    CONSULTA_ANTECEDENCIA_MAXIMA,
    CONSULTA_DURACAO_MINUTOS,
)
from datetime import datetime, UTC
from terapia.utilidades.geral import desprezar_segundos_e_microssegundos
from usuario.models import Usuario
    

def validate_antecedencia(data_hora):
    agora = timezone.now()

    if data_hora < agora + CONSULTA_ANTECEDENCIA_MINIMA:
        raise ValidationError(
            "A consulta deve ser agendada com, no mínimo, %(antecedencia)s minutos de antecedência.",
            params={'antecedencia': CONSULTA_ANTECEDENCIA_MINIMA.total_seconds() // 60},
            code='antecedencia_minima_nao_atendida',
        )
    elif data_hora > agora + CONSULTA_ANTECEDENCIA_MAXIMA:
        raise ValidationError(
            "A consulta não pode ser agendada para mais de %(antecedencia_maxima) dias no futuro.",
            params={'antecedencia_maxima': CONSULTA_ANTECEDENCIA_MAXIMA.days},
            code='antecedencia_maxima_nao_atendida',
        )


def validate_divisivel_por_duracao_consulta(data_hora):
    data_hora = timezone.localtime(desprezar_segundos_e_microssegundos(data_hora), UTC)
    meia_noite = data_hora.replace(hour=0, minute=0)
    total_minutos = int((data_hora - meia_noite).total_seconds() // 60)

    if total_minutos % CONSULTA_DURACAO_MINUTOS != 0:
        raise ValidationError(
            "A data-hora deve ser um múltiplo de %(multiplo)s minutos no fuso-horário UTC.",
            params={"multiplo": CONSULTA_DURACAO_MINUTOS},
            code="data_hora_nao_divisivel_por_duracao_consulta",
        )


def validate_valor_consulta(valor):
    """
    Garante que o valor da consulta esteja entre R$ 20,00 e R$ 4.999,99.
    """
    if valor is None:
        return
    min_value = Decimal("20.00")
    max_value = Decimal("4999.99")
    if valor < min_value or valor > max_value:
        raise ValidationError(
            "O valor da consulta deve ser entre R$%(min_value)s e R$%(max_value)s.",
            params={"min_value": min_value, "max_value": max_value},
            code="valor_consulta_invalido",
        )
    

def validate_intervalo_disponibilidade_data_hora_range(data_hora):
    """
    Garante que a data-hora esteja entre 00:00 de 01/07/2024 e 23:59 de 07/07/2024.
    """
    data_hora_minima = datetime(2024, 7, 1, 0, 0, tzinfo=data_hora.tzinfo)
    data_hora_maxima = datetime(2024, 7, 7, 23, 59, tzinfo=data_hora.tzinfo)

    if not (data_hora_minima <= data_hora <= data_hora_maxima):
        raise ValidationError(
            "A data-hora deve estar entre %(data_hora_minima)s e %(data_hora_maxima)s.",
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
