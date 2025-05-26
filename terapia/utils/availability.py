from __future__ import annotations

from datetime import timedelta
from typing import TypedDict, List, Optional
from django.core.exceptions import ValidationError
from terapia.constants import CONSULTA_DURACAO_MAXIMA


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
    dia_semana: int  #  1 (domingo) … 7 (sábado)
    intervalos: List[Intervalo]


def to_timedelta(horario: str) -> timedelta:
    """
    Converte string "HH:MM" para timedelta.
    Retorna None se o formato for inválido.
    """
    try:
        h, m = map(int, horario.split(":"))
        td = timedelta(hours=h, minutes=m)

        if td > timedelta(days=1):
            raise ValueError
        
        return td

    except ValueError:
        return None
    

def esta_no_intervalo(
    instante: timedelta,
    intervalo: Intervalo | None,
) -> bool:
    """
    Verifica se o instante está contido no intervalo, incluindo limites.
    Se o intervalo for None, retorna False.
    """
    if intervalo is None:
        return False
    
    inicio = to_timedelta(intervalo["horario_inicio"])
    fim = to_timedelta(intervalo["horario_fim"])

    return inicio <= instante <= fim


def validate_disponibilidade(
        data: Optional[List[Disponibilidade]]
) -> None:
    """
    Valida o atributo disponibilidade em dois aspectos:
    1) estrutura do JSON;
    2) horários (formato correto, início < fim, duração mínima de 1 consulta, sem sobreposição de intervalos).
    """
    validate_disponibilidade_json(data)
    validate_disponibilidade_horarios(data)


def validate_disponibilidade_json(data):
    """
    Valida a estrutura JSON de disponibilidade.

    - Garante que seja uma lista de objetos ou uma lista vazia.
    - Cada objeto deve ter 'dia_semana' (int 1-7) e 'intervalos' (lista de dicionários).
    - Cada intervalo deve conter as chaves 'horario_inicio' e 'horario_fim', não podendo conter outras.
    """
    if not isinstance(data, list):
        raise ValidationError("Disponibilidade deve ser uma lista de objetos ou uma lista vazia")

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
    - Garante que o intervalo tenha pelo menos 1 consulta de duração.
    - Garante que não haja sobreposição de intervalos.
    """
    for i, item in enumerate(data):
        for j, intervalo in enumerate(item["intervalos"]):
            horario_inicio = to_timedelta(intervalo["horario_inicio"])
            horario_fim = to_timedelta(intervalo["horario_fim"])

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

            # Valida que o intervalo tem pelo menos 1 consulta de duração
            if horario_fim - horario_inicio < CONSULTA_DURACAO_MAXIMA:
                raise ValidationError(
                    f"Item #{i}.intervalos[{j}]: o intervalo deve ter pelo menos 1 consulta ({CONSULTA_DURACAO_MAXIMA.total_seconds() / 60:.0f} minutos) de duração"
                )
            
            # Valida que o horário termine em :00
            if not (horario_inicio.seconds % 3600 == 0 and horario_fim.seconds % 3600 == 0):
                raise ValidationError(
                    f"Item #{i}.intervalos[{j}]: os horários devem terminar em :00"
                )
            
            
        # Valida que não há sobreposição de intervalos
        for j, intervalo in enumerate(item["intervalos"]):
            horario_inicio = to_timedelta(intervalo["horario_inicio"])
            horario_fim = to_timedelta(intervalo["horario_fim"])

            for k in range(len(item["intervalos"])):
                if k == j:
                    continue

                outro_intervalo = item["intervalos"][k]

                if esta_no_intervalo(horario_inicio, outro_intervalo) \
                or esta_no_intervalo(horario_fim, outro_intervalo):
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
                {"horario_inicio": "13:00", "horario_fim": "14:00"},
                {"horario_inicio": "08:00", "horario_fim": "12:00"},
                {"horario_inicio": "06:30", "horario_fim": "07:30"},
            ]
        }],

        # 23
        [{
            "dia_semana": 5,
            "intervalos": [
                {"horario_inicio": "24:00", "horario_fim": "03:00"},
            ]
        }],

        # 24
        [{
            "dia_semana": 5,
            "intervalos": [
                {"horario_inicio": "00:00", "horario_fim": "24:00"},
            ]
        }],

        # 25
        [{
            "dia_semana": 5,
            "intervalos": [
                {"horario_inicio": "13:00", "horario_fim": "14:00"},
                {"horario_inicio": "08:00", "horario_fim": "12:00"},
                {"horario_inicio": "06:00", "horario_fim": "07:00"},
            ]
        }],

        # 26
        [{
            "dia_semana": 5,
            "intervalos": [
                {"horario_inicio": "13:00", "horario_fim": "14:00"},
                {"horario_inicio": "08:00", "horario_fim": "12:00"},
                {"horario_inicio": "06:00", "horario_fim": "07:00"},
            ]
        }],
    ]

    for i, disp in enumerate(disponibilidades_json):
        print(f"Testando disponibilidade #{i}", end=": ")
        try:
            validate_disponibilidade(disp)
            print("OK")
        except ValidationError as e:
            print(e)


if __name__ == '__main__':
    main()
