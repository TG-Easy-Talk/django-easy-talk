from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, date
from itertools import groupby
from typing import List

from django.utils import timezone

MatrizSemana = List[List[bool]]
HORAS_SEMANA = 7 * 24


@dataclass(frozen=True)
class BlocoHoras:
    inicio: int
    fim: int


def nova_matriz_vazia() -> MatrizSemana:
    return [[False] * 24 for _ in range(7)]


def segunda_para_domingo(m: MatrizSemana) -> MatrizSemana:
    return [m[6]] + m[:6]


def domingo_para_segunda(m: MatrizSemana) -> MatrizSemana:
    if len(m) == 7 and len(m[0]) == 24:
        pass
    return m[1:] + [m[0]]


def matriz_para_json_js(m: MatrizSemana) -> str:
    return json.dumps(m)


def flatten_semana(m: MatrizSemana) -> List[bool]:
    return [flag for dia in m for flag in dia]


def unflatten_semana(v: List[bool]) -> MatrizSemana:
    return [v[i * 24:(i + 1) * 24] for i in range(7)]


def marcar_intervalo_na_matriz(
        m: MatrizSemana,
        dia_semana_1a7: int,
        hora_ini: int,
        hora_fim: int
) -> None:
    idx_dia = dia_semana_1a7 - 1
    hora_ini = max(0, min(23, hora_ini))
    hora_fim = max(0, min(24, hora_fim))
    for h in range(hora_ini, hora_fim):
        m[idx_dia][h] = True


def disponibilidade_queryset_para_matriz(disponibilidade_qs) -> MatrizSemana:
    m = nova_matriz_vazia()
    if not disponibilidade_qs.exists():
        return m

    for intervalo in disponibilidade_qs.all():
        di = max(1, min(7, intervalo.dia_semana_inicio_local))
        df = max(1, min(7, intervalo.dia_semana_fim_local))
        hi = int(intervalo.hora_inicio_local.hour)
        hf = int(intervalo.hora_fim_local.hour)

        abs_ini = (di - 1) * 24 + hi
        abs_fim = (df - 1) * 24 + hf

        if abs_fim <= abs_ini:
            abs_fim += HORAS_SEMANA

        for h_abs in range(abs_ini, abs_fim):
            dia = (h_abs // 24) % 7
            hora = h_abs % 24
            m[dia][hora] = True

    return m


def extrair_blocos_contiguos(v: List[bool]) -> List[BlocoHoras]:
    blocos: List[BlocoHoras] = []
    idx = 0
    for valor, grupo in groupby(
            v):
        tamanho = sum(1 for _ in grupo)
        if valor:
            blocos.append(BlocoHoras(inicio=idx, fim=idx + tamanho))
        idx += tamanho
    if len(blocos) >= 2 and blocos[0].inicio == 0 and blocos[-1].fim == HORAS_SEMANA:
        primeiro = blocos.pop(0)
        ultimo = blocos.pop()
        blocos.append(BlocoHoras(inicio=ultimo.inicio, fim=primeiro.fim + HORAS_SEMANA))

    return blocos


def matriz_para_intervalos(
        m: MatrizSemana,
        psicologo=None,
        base_segunda: date | None = None,
) -> list:
    from terapia.models import IntervaloDisponibilidade

    tz = timezone.get_current_timezone()
    if base_segunda is None:
        hoje_local = timezone.localtime(timezone.now())
        delta_dias = (hoje_local.isoweekday() - 1)
        base_naive = datetime(hoje_local.year, hoje_local.month, hoje_local.day) - timedelta(days=delta_dias)
    else:
        base_naive = datetime.combine(base_segunda, datetime.min.time())

    base = timezone.make_aware(base_naive, tz)

    v = flatten_semana(m)
    blocos = extrair_blocos_contiguos(v)

    intervalos = []
    for b in blocos:
        inicio_dt = base + timedelta(hours=b.inicio)
        fim_dt = base + timedelta(hours=b.fim)
        obj = IntervaloDisponibilidade(data_hora_inicio=inicio_dt, data_hora_fim=fim_dt)
        if psicologo is not None:
            obj.psicologo = psicologo
        intervalos.append(obj)

    return intervalos


def get_matriz_disponibilidade_booleanos_em_javascript(disponibilidade, **_) -> str:
    m_segunda = disponibilidade_queryset_para_matriz(disponibilidade)
    m_domingo = segunda_para_domingo(m_segunda)
    return matriz_para_json_js(m_domingo)


def get_disponibilidade_pela_matriz(matriz_domingo_sabado: MatrizSemana, psicologo=None, **_) -> list:
    m_segunda = domingo_para_segunda(matriz_domingo_sabado)
    return matriz_para_intervalos(m_segunda, psicologo=psicologo)
