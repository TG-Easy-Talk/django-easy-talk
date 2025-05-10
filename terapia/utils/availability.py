from __future__ import annotations

import datetime as _dt
from datetime import datetime, time, timedelta
from typing import TypedDict, List, Optional, Any
from django.core.exceptions import ValidationError


TIME_FMT = "%H:%M"


class Intervalo(TypedDict):
    """
    Representa um intervalo de tempo no formato de strings "HH:MM".
    """
    horario_inicio: str
    horario_fim: str


class Disponibilidade(TypedDict):
    """
    Representa a disponibilidade semanal de um psicólogo,
    associando dia da semana a uma lista de intervalos.
    """
    dia_semana: int  # ISO weekday: 1 (segunda) … 7 (domingo)
    intervalos: List[Intervalo]


def parse_time(s: str) -> time | None:
    """
    Converte string "HH:MM" para datetime.time.
    Retorna None se o formato for inválido.
    """
    try:
        return datetime.strptime(s, TIME_FMT).time()
    except (ValueError, TypeError):
        return None


def is_in_interval(
        now: time,
        start: time | None,
        end: time | None
) -> bool:
    """
    Retorna True se now estiver entre start e end, incluindo limites.
    Se start ou end for None, retorna False.
    """
    if start is None or end is None:
        return False
    return start <= now <= end


def validate_disponibilidade_json(
        data: Optional[List[Disponibilidade]]
) -> None:
    """
    Valida a estrutura JSON de disponibilidade.

    - Garante que seja uma lista de objetos.
    - Cada objeto deve ter 'dia_semana' (int 1–7) e 'intervalos' (lista de dicionários).
    - Cada intervalo deve conter 'horario_inicio' e 'horario_fim' no formato HH:MM.
    """
    if data is None:
        return

    if not isinstance(data, list):
        raise ValidationError("Disponibilidade deve ser uma lista de objetos")

    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValidationError(f"Item #{i} não é um dicionário")

        dia = item.get("dia_semana")
        intervalos = item.get("intervalos")

        if not isinstance(dia, int) or not (1 <= dia <= 7):
            raise ValidationError(f"Item #{i}: a chave 'dia_semana' pode estar faltando ou não ser um int de 1 a 7")

        if not isinstance(intervalos, list):
            raise ValidationError(f"Item #{i}: a chave 'intervalos' pode estar faltando ou não ser uma lista")

        for j, intervalo in enumerate(intervalos):
            if not isinstance(intervalo, dict):
                raise ValidationError(f"Item #{i}.intervalos[{j}] não é um dicionário")
            
            if intervalo.keys() != {"horario_inicio", "horario_fim"}:
                raise ValidationError(
                    f"Item #{i}.intervalos[{j}] precisa das chaves 'horario_inicio' e 'horario_fim', não podendo conter outras chaves."
                )

            horario_inicio = parse_time(intervalo["horario_inicio"])
            horario_fim = parse_time(intervalo["horario_fim"])

            # Valida o formato de horário
            if horario_inicio is None or horario_fim is None:
                raise ValidationError(
                    f"Item #{i}.intervalos[{j}]: formato de horário inválido"
                )
            
            # Convert time objects to datetime objects for the same day
            datetime_inicio = datetime.combine(datetime.today(), horario_inicio)
            datetime_fim = datetime.combine(datetime.today(), horario_fim)

            # Calculate the difference
            difference = datetime_fim - datetime_inicio

            # Check if the difference is at least 1 hour
            if difference < timedelta(hours=1):
                raise ValidationError(
                    f"Item #{i}.intervalos[{j}]: o horário de fim deve ser, no mínimo, 1 hora depois do horário de início"
                )


def check_psicologo_disponibilidade(
        psicologo: Any,
        data_hora: _dt.datetime
) -> bool:
    """
    Retorna True se 'data_hora' cai dentro de algum intervalo
    da lista psicologo.disponibilidade.

    - Usa any() para interromper ao encontrar o primeiro intervalo válido.
    - Trata disponibilidade ausente ou None como lista vazia.
    """
    dispon: List[Disponibilidade] = getattr(psicologo, "disponibilidade", []) or []
    hoje = data_hora.isoweekday()
    agora = data_hora.time()

    return any(
        is_in_interval(
            agora,
            parse_time(intervalo["horario_inicio"]),
            parse_time(intervalo["horario_fim"])
        )
        for disp in dispon
        if disp.get("dia_semana") == hoje
        for intervalo in disp.get("intervalos", [])
    )

# O código daqui pra baixo é provisório
# e deve ser transformado em testes unitários no futuro.
def main():
    disponibilidades_json = [
        # 0
        None,

        # 1
        [None],

        # 2
        [
            {
                "intervalos": [
                    {"horario_inicio": "08:00", "horario_fim": "12:00"},
                    {"horario_inicio": "14:00", "horario_fim": "18:00"}
                ]
            },
        ],

        # 3
        [
            {
                "dia_semana": 1,
            },
        ],

        # 4
        [
            {
                "dia_semana": 0,
                "intervalos": [
                    {"horario_inicio": "08:00", "horario_fim": "12:00"},
                    {"horario_inicio": "14:00", "horario_fim": "18:00"}
                ]
            },
        ],

        # 5
        [
            {
                "dia_semana": "não é um int",
                "intervalos": [
                    {"horario_inicio": "08:00", "horario_fim": "12:00"},
                    {"horario_inicio": "14:00", "horario_fim": "18:00"}
                ]
            },
        ],

        # 6
        [
            {
                "dia_semana": 1,
                "intervalos": "não é uma lista",
            },
        ],

        # 7
        [
            {
                "dia_semana": 5,
                "intervalos": [
                    {"horario_inicio": "08:00", "horario_fim": "12:00", "chave_adicional_que_não_deve_existir": "valor_qualquer"},
                    {"horario_inicio": "14:00", "horario_fim": "18:00"}
                ]
            },
        ],

        # 8
        [
            {
                "dia_semana": 5,
                "intervalos": [
                    {"horario_inicio": "08:00"},
                    {"horario_inicio": "14:00", "horario_fim": "18:00"}
                ]
            },
        ],

        # 9
        [
            {
                "dia_semana": 5,
                "intervalos": [
                    {"horario_fim": "18:00"}
                ]
            },
        ],

        # 10
        [
            {
                "dia_semana": 5,
                "intervalos": [
                    {"horario_inicio": "08:00", "horario_fim": "12:00"},
                    "valor que não é dicionário",
                ]
            },
        ],

        # 11
        [
            {
                "dia_semana": 5,
                "intervalos": [
                    {"horario_inicio": "08:00", "horario_fim": "12:00"},
                    {"horario_inicio": "25:00", "horario_fim": "26:00"},
                ]
            },
        ],

        # 12
        [
            {
                "dia_semana": 5,
                "intervalos": [
                    {"horario_inicio": "08:00", "horario_fim": "12:00"},
                    {"horario_inicio": "12:00", "horario_fim": "11:00"},
                ]
            },
        ],

        # 13
        [
            {
                "dia_semana": 5,
                "intervalos": [
                    {"horario_inicio": "08:00", "horario_fim": "12:00"},
                    {"horario_inicio": "11:00", "horario_fim": "11:59"},
                ]
            },
        ],

        # 14
        [
            {
                "dia_semana": 5,
                "intervalos": [
                    {"horario_inicio": "08:00", "horario_fim": "12:00"},
                    {"horario_inicio": "11:30", "horario_fim": "12:30"},
                ]
            },
        ],
    ]

    for i, disponibilidade in enumerate(disponibilidades_json):
        print(f"Testando disponibilidade #{i}", end=": ")
        try:
            validate_disponibilidade_json(disponibilidade)
            print("OK")
        except ValidationError as e:
            print(e)


if __name__ == '__main__':
    main()
