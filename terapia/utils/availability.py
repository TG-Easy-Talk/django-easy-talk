from __future__ import annotations

import datetime as _dt
from datetime import datetime, time
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


def validate_disponibilidade(
        data: Optional[List[Disponibilidade]]
) -> None:
    """
    Valida o atributo disponibilidade em dois aspectos:
    1) estrutura do JSON;
    2) horários (formato correto, início < fim, duração mínima de 1 hora, sem sobreposição de intervalos).
    """
    validate_disponibilidade_json(data)
    validate_disponibilidade_horarios(data)


def validate_disponibilidade_json(data):
    """
    Valida a estrutura JSON de disponibilidade.

    - Garante que seja uma lista de objetos.
    - Cada objeto deve ter 'dia_semana' (int 1–7) e 'intervalos' (lista de dicionários).
    - Cada intervalo deve conter as chaves 'horario_inicio' e 'horario_fim', não podendo conter outras.
    """
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
            

def validate_disponibilidade_horarios(data):
    """
    Valida os horários de início e fim dos intervalos.

    - Garante que o horário esteja no formato "HH:MM".
    - Garante que o horário esteja dentro do intervalo de 00:00 a 23:59.
    - Garante que o horário de início seja menor que o horário de fim.
    - Garante que o intervalo tenha pelo menos 1 hora de duração.
    - Garante que não haja sobreposição de intervalos.
    """
    for i, item in enumerate(data):
        for j, intervalo in enumerate(item["intervalos"]):
            horario_inicio = parse_time(intervalo["horario_inicio"])
            horario_fim = parse_time(intervalo["horario_fim"])

            # Valida o formato de horário
            if horario_inicio is None or horario_fim is None:
                raise ValidationError(
                    f"Item #{i}.intervalos[{j}]: formato de horário inválido"
                )

            # Valida que o horário de início é menor que o horário de fim
            if horario_inicio >= horario_fim:
                raise ValidationError(
                    f"Item #{i}.intervalos[{j}]: o horário de início deve ser menor que o horário de fim"
                )

            # Valida a duração mínima de 1 hora
            if (horario_fim.hour - horario_inicio.hour) < 1:
                raise ValidationError(
                    f"Item #{i}.intervalos[{j}]: o horário de fim deve ser, no mínimo, 1 hora depois do horário de início"
                )
            
            
        # Valida que não há sobreposição de intervalos
        for j, intervalo in enumerate(item["intervalos"]):
            horario_inicio = parse_time(intervalo["horario_inicio"])
            horario_fim = parse_time(intervalo["horario_fim"])

            for k in range(len(item["intervalos"])):
                if k == j:
                    continue

                outro_horario_inicio = parse_time(item["intervalos"][k]["horario_inicio"])
                outro_horario_fim = parse_time(item["intervalos"][k]["horario_fim"])

                if is_in_interval(horario_inicio, outro_horario_inicio, outro_horario_fim) \
                or is_in_interval(horario_fim, outro_horario_inicio, outro_horario_fim):
                    raise ValidationError(
                        f"Item #{i}.intervalos[{j}] e item #{i}.intervalos[{k}]: os intervalos se sobrepõem"
                    )










######################################################################
# O código daqui pra baixo é provisório
# e deve ser transformado em testes unitários no futuro.
######################################################################
def main():
    disponibilidades_json = [
        # 0
        None,

        # 1
        [None],

        # 2
        [{
            "intervalos": [
                {"horario_inicio": "08:00", "horario_fim": "12:00"},
                {"horario_inicio": "14:00", "horario_fim": "18:00"}
            ]
        }],

        # 3
        [{
            "dia_semana": 1,
        }],

        # 4
        [{
            "dia_semana": 0,
            "intervalos": [
                {"horario_inicio": "08:00", "horario_fim": "12:00"},
                {"horario_inicio": "14:00", "horario_fim": "18:00"}
            ]
        }],

        # 5
        [{
            "dia_semana": "não é um int",
            "intervalos": [
                {"horario_inicio": "08:00", "horario_fim": "12:00"},
                {"horario_inicio": "14:00", "horario_fim": "18:00"}
            ]
        }],

        # 6
        [{
            "dia_semana": 1,
            "intervalos": "não é uma lista",
        }],

        # 7
        [{
            "dia_semana": 5,
            "intervalos": [
                {"horario_inicio": "08:00", "horario_fim": "12:00", "chave_adicional_que_não_deve_existir": "valor_qualquer"},
                {"horario_inicio": "14:00", "horario_fim": "18:00"}
            ]
        }],

        # 8
        [{
            "dia_semana": 5,
            "intervalos": [
                {"horario_inicio": "08:00"},
                {"horario_inicio": "14:00", "horario_fim": "18:00"}
            ]
        }],

        # 9
        [{
            "dia_semana": 5,
            "intervalos": [
                {"horario_fim": "18:00"}
            ]
        }],

        # 10
        [{
            "dia_semana": 5,
            "intervalos": [
                {"horario_inicio": "08:00", "horario_fim": "12:00"},
                "valor que não é dicionário",
            ]
        }],

        # 11
        [{
            "dia_semana": 5,
            "intervalos": [
                {"horario_inicio": "08:00", "horario_fim": "12:00"},
                {"horario_inicio": "25:00", "horario_fim": "26:00"},
            ]
        }],

        # 12
        [{
            "dia_semana": 5,
            "intervalos": [
                {"horario_inicio": "08:00", "horario_fim": "12:00"},
                {"horario_inicio": "12:00", "horario_fim": "11:00"},
            ]
        }],

        # 13
        [{
            "dia_semana": 5,
            "intervalos": [
                {"horario_inicio": "08:00", "horario_fim": "12:00"},
                {"horario_inicio": "11:00", "horario_fim": "11:59"},
            ]
        }],

        # 14
        [{
            "dia_semana": 5,
            "intervalos": [
                {"horario_inicio": "08:00", "horario_fim": "12:00"},
                {"horario_inicio": "11:30", "horario_fim": "12:30"},
            ]
        }],

        # 15
        [{
            "dia_semana": 5,
            "intervalos": [
                {"horario_inicio": "08:00", "horario_fim": "12:00"},
                {"horario_inicio": "13:00", "horario_fim": "15:00"},
                {"horario_inicio": "16:30", "horario_fim": "16:25"},
                {"horario_inicio": "19:30", "horario_fim": "20:30"},
            ]
        }],

        # 16
        [{
            "dia_semana": 5,
            "intervalos": [
                {"horario_inicio": "08:00", "horario_fim": "12:00"},
                {"horario_inicio": "09:00", "horario_fim": "13:00"},
            ]
        }],

        # 17
        [{
            "dia_semana": 5,
            "intervalos": [
                {"horario_inicio": "08:00", "horario_fim": "12:00"},
                {"horario_inicio": "08:00", "horario_fim": "14:00"},
            ]
        }],

        # 18
        [{
            "dia_semana": 5,
            "intervalos": [
                {"horario_inicio": "08:00", "horario_fim": "12:00"},
                {"horario_inicio": "12:00", "horario_fim": "14:00"},
            ]
        }],

        # 19
        [{
            "dia_semana": 5,
            "intervalos": [
                {"horario_inicio": "08:00", "horario_fim": "12:00"},
                {"horario_inicio": "13:00", "horario_fim": "14:00"},
                {"horario_inicio": "07:00", "horario_fim": "08:00"},
            ]
        }],

        # 20
        [{
            "dia_semana": 5,
            "intervalos": [
                {"horario_inicio": "06:00", "horario_fim": "14:00"},
                {"horario_inicio": "08:00", "horario_fim": "12:00"},
            ]
        }],

        # 21
        [{
            "dia_semana": 5,
            "intervalos": [
                {"horario_inicio": "08:00", "horario_fim": "12:00"},
                {"horario_inicio": "06:00", "horario_fim": "14:00"},
            ]
        }],

        # 22
        [{
            "dia_semana": 5,
            "intervalos": [
                {"horario_inicio": "00:00", "horario_fim": "24:00"},
            ]
        }],

        # 23
        [{
            "dia_semana": 5,
            "intervalos": [
                {"horario_inicio": "08:00", "horario_fim": "12:00"},
                {"horario_inicio": "13:00", "horario_fim": "14:00"},
                {"horario_inicio": "06:30", "horario_fim": "07:30"},
            ]
        }],
    ]

    for i, disponibilidade in enumerate(disponibilidades_json):
        print(f"Testando disponibilidade #{i}", end=": ")
        try:
            validate_disponibilidade(disponibilidade)
            print("OK")
        except ValidationError as e:
            print(e)


if __name__ == '__main__':
    main()
