# django-easy-talk/terapia/utils/disponibilidade.py

from datetime import time, datetime, timedelta
from django.utils import timezone

MAX_PROPAGATION_WEEKS = 52  # Limite anual

def get_matriz_disponibilidade_booleanos_em_javascript(disponibilidade, week_offset=0):
    """
    Gera a matriz semanal de disponibilidade para a semana atual + offset.
    Cada linha é um dia (0 = segunda-feira, 6 = domingo) e cada coluna uma hora (0–23).
    """
    tz = timezone.get_current_timezone()
    hoje = timezone.localtime(timezone.now(), tz).date()
    # calcula o início da semana (segunda-feira) com deslocamento de semanas
    inicio_semana = hoje - timedelta(days=hoje.isoweekday() - 1) + timedelta(weeks=week_offset)

    # filtra apenas os IntervaloDisponibilidade que começam nesta semana
    semanal = disponibilidade.filter(
        data_hora_inicio__gte=datetime.combine(inicio_semana, time.min, tzinfo=tz),
        data_hora_inicio__lt =datetime.combine(inicio_semana + timedelta(days=7), time.min, tzinfo=tz)
    )

    # inicializa matriz 7x24 toda em False
    matriz = [[False] * 24 for _ in range(7)]

    # marca True em cada hora disponível
    for intervalo in semanal:
        start = timezone.localtime(intervalo.data_hora_inicio, tz)
        end = timezone.localtime(intervalo.data_hora_fim, tz)
        current = start
        while current < end:
            dia_idx = (current.date() - inicio_semana).days
            if 0 <= dia_idx < 7:
                matriz[dia_idx][current.hour] = True
            current += timedelta(hours=1)

    # converte para string lower-case para consumo em JavaScript
    return str(matriz).lower()


def get_disponibilidade_pela_matriz(matriz, week_offset=0, propagate=True):
    """
    Converte a matriz de booleanos (JSON) em instâncias de IntervaloDisponibilidade.

    - propagate=True: replica os intervalos para todas as semanas futuras (até MAX_PROPAGATION_WEEKS).
    - propagate=False: gera apenas os intervalos da semana week_offset.
    """
    # importa localmente para evitar circular import
    from terapia.models import IntervaloDisponibilidade

    tz = timezone.get_current_timezone()
    hoje = timezone.localtime(timezone.now(), tz).date()
    inicio_semana = hoje - timedelta(days=hoje.isoweekday() - 1) + timedelta(weeks=week_offset)

    intervalos = []
    semanas = range(week_offset, MAX_PROPAGATION_WEEKS) if propagate else [week_offset]

    for dia, linha in enumerate(matriz):
        j = 0
        while j < 24:
            if linha[j]:
                hora_inicio = j
                while j < 24 and linha[j]:
                    j += 1
                hora_fim = j
                # para cada semana alvo, crie um IntervaloDisponibilidade
                for w in semanas:
                    semana_base = inicio_semana + timedelta(weeks=(w - week_offset))
                    dt_inicio = datetime.combine(
                        semana_base + timedelta(days=dia),
                        time(hora_inicio),
                        tzinfo=tz
                    )
                    dt_fim = datetime.combine(
                        semana_base + timedelta(days=dia),
                        time(hora_fim),
                        tzinfo=tz
                    )
                    intervalos.append(IntervaloDisponibilidade(
                        data_hora_inicio=dt_inicio,
                        data_hora_fim=dt_fim
                    ))
            else:
                j += 1

    return intervalos
