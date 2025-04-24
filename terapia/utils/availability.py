import datetime as _dt
from typing import List, Dict, Any
from django.core.exceptions import ValidationError

Intervalo = Dict[str, str]  # {"horario_inicio": "08:00", "horario_fim": "12:00"}
Disponibilidade = Dict[str, Any]  # {"dia_semana": 1, "intervalos": [Intervalo]}


def validate_disponibilidade_json(data: List[Disponibilidade] | None) -> None:
    if data is None:
        return
    if not isinstance(data, list):
        raise ValidationError("O JSON de disponibilidade está em formato incorreto")
    for item in data:
        if (not isinstance(item, dict)
                or "dia_semana" not in item
                or "intervalos" not in item
                or not isinstance(item["intervalos"], list)):
            raise ValidationError("O JSON de disponibilidade está em formato incorreto")
        for intr in item["intervalos"]:
            if (not isinstance(intr, dict)
                    or not all(k in intr for k in ("horario_inicio", "horario_fim"))):
                raise ValidationError("O JSON de disponibilidade está em formato incorreto")


def check_psicologo_disponibilidade(psicologo, data_hora: _dt.datetime) -> bool:
    disp = psicologo.disponibilidade or []
    dia = data_hora.isoweekday()
    hora = data_hora.time()
    for item in disp:
        if item.get("dia_semana") != dia:
            continue
        for intr in item["intervalos"]:
            try:
                start = _dt.datetime.strptime(intr["horario_inicio"], "%H:%M").time()
                end = _dt.datetime.strptime(intr["horario_fim"], "%H:%M").time()
            except (KeyError, ValueError):
                continue
            if start <= hora <= end:
                return True
    return False
