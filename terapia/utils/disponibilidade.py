from datetime import datetime
from django.utils import timezone


def get_matriz_disponibilidade_booleanos_em_javascript(disponibilidade, **_):
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
    return str(matriz).lower()


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


def get_disponibilidade_pela_matriz(matriz_disponibilidade_booleanos, psicologo=None, **_):
    """
    Converte a matriz de booleanos em JavaScript em objetos de IntervaloDisponibilidade.
    """
    from terapia.models import IntervaloDisponibilidade
    
    segunda_a_domingo(matriz_disponibilidade_booleanos)
    m = matriz_disponibilidade_booleanos

    tz = timezone.get_current_timezone()
    base_monday = datetime(2024, 7, 1, tzinfo=tz)

    disponibilidade = []

    for i in range(7):
        j = 0
        while j < 24:
            if m[i][j]:
                start_i, start_h = i, j
                k_i, k_h = i, j

                while True:
                    k_h += 1
                    if k_h == 24:
                        k_h = 0
                        k_i += 1

                    if k_i >= 7:
                        end_dt = base_monday + timedelta(days=7)  # segunda 00:00 da semana seguinte
                        break

                    if not m[k_i][k_h]:
                        end_dt = base_monday + timedelta(days=k_i, hours=k_h)
                        break

                start_dt = base_monday + timedelta(days=start_i, hours=start_h)
                intervalo = IntervaloDisponibilidade(
                    data_hora_inicio=start_dt,
                    data_hora_fim=end_dt,
                )
                if psicologo is not None:
                    intervalo.psicologo = psicologo

                disponibilidade.append(intervalo)

                p_i, p_h = start_i, start_h
                while True:
                    m[p_i][p_h] = False
                    if p_i == k_i and p_h == k_h:
                        break
                    p_h += 1
                    if p_h == 24:
                        p_h = 0
                        p_i += 1
                        if p_i >= 7:
                            break

                if i == k_i:
                    j = k_h
                else:
                    break
            else:
                j += 1

    return disponibilidade
