from datetime import time, datetime, date
from django.utils import timezone


def get_matriz_disponibilidade_booleanos_em_javascript(disponibilidade):
    """
    Cria uma matriz de booleanos que representa a disponibilidade.
    A ideia é que a matriz seja interpretável nos templates, então
    ela é retornada como uma string que pode ser decodificada pelo
    JavaScript no template.
    """
    matriz = [[False] * 24 for _ in range(7)]

    if disponibilidade.exists():
        for intervalo in disponibilidade.all():
            dia_semana_inicio = intervalo.dia_semana_inicio_local - 1
            dia_semana_fim = intervalo.dia_semana_fim_local - 1
            hora_inicio = intervalo.hora_inicio_local.hour
            hora_fim = intervalo.hora_fim_local.hour

            ranges = []

            if dia_semana_inicio == dia_semana_fim:
                ranges = [range(hora_inicio, hora_fim)]
            else:
                ranges.append(range(hora_inicio, 24))
                i = dia_semana_inicio + 1

                while i <= dia_semana_fim:
                    if i != dia_semana_fim:
                        ranges.append(range(0, 24))
                    else:
                        ranges.append(range(0, hora_fim))
                    i += 1

            for i, _range in enumerate(ranges):
                for hora in _range:
                    matriz[(dia_semana_inicio + i) % 7][hora] = True

    domingo_a_segunda(matriz)
    # Usar str.lower() para o JavaScript interpretar corretamente
    matriz_em_javascript = str(matriz).lower()
    return matriz_em_javascript


def segunda_a_domingo(matriz_disponibilidade_booleanos):
    """
    Converte uma matriz de domingo a sábado para uma matriz de segunda a domingo.
    """
    matriz_disponibilidade_booleanos.append(matriz_disponibilidade_booleanos.pop(0))


def domingo_a_segunda(matriz_disponibilidade_booleanos):
    """
    Converte uma matriz de segunda a domingo para uma matriz de domingo a sábado.
    """
    matriz_disponibilidade_booleanos.insert(0, matriz_disponibilidade_booleanos.pop())


def get_disponibilidade_pela_matriz(matriz_disponibilidade_booleanos):
    """
    Converte a matriz de booleanos em JavaScript em objetos de IntervaloDisponibilidade.
    """
    from terapia.models import IntervaloDisponibilidade
    
    segunda_a_domingo(matriz_disponibilidade_booleanos)

    disponibilidade = []
    m = matriz_disponibilidade_booleanos

    i = j = 0
    while i < len(m):
        while j < len(m[i]):
            if m[i][j]:
                hora_inicio = time(j, 0)
                dia_semana_inicio = i + 1 # Somar 1 para ficar no formato ISO de dias de semana (1 = Segunda, 7 = Domingo)

                while m[i][j]:
                    if j < len(m[i]) - 1:
                        j += 1
                    else:
                        i += 1
                        if i >= len(m):
                            break
                        j = 0

                j = j if j < 23 else 0
                hora_fim = time(j, 0)
                dia_semana_fim = i + 1 # Somar 1 para ficar no formato ISO de dias de semana (1 = Segunda, 7 = Domingo)
                fuso_atual = timezone.get_current_timezone()

                intervalo = IntervaloDisponibilidade(
                    data_hora_inicio=datetime.combine(date(2024, 7, dia_semana_inicio), hora_inicio, tzinfo=fuso_atual),
                    data_hora_fim=datetime.combine(date(2024, 7, dia_semana_fim), hora_fim, tzinfo=fuso_atual),
                )

                disponibilidade.append(intervalo)

            j += 1

            if i >= len(m):
                break

        i += 1
        j = 0

    return disponibilidade
