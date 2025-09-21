from datetime import date, datetime, time, UTC
from django.utils import timezone
from terapia.constantes import CONSULTA_DURACAO, NUMERO_PERIODOS_POR_DIA


def regra_de_3_numero_periodos_por_dia(n):
        """
        Recebe um número "n" que representa um horário num dia de 24 horas e retorna
        o seu correspondente num dia de NUMERO_PERIODOS_POR_DIA horas.

        Exemplo: se n=6 e NUMERO_PERIODOS_POR_DIA=12, então a função retorna 3.
        """
        return int(n * NUMERO_PERIODOS_POR_DIA // 24)


def segunda_a_domingo(matriz_disponibilidade_booleanos):
    """
    Converte uma matriz de domingo a sábado para uma matriz de segunda a domingo.
    """
    matriz_disponibilidade_booleanos.append(matriz_disponibilidade_booleanos.pop(0))


def get_disponibilidade_pela_matriz(matriz_disponibilidade_booleanos):
    """
    Converte a matriz de booleanos JSON em objetos de IntervaloDisponibilidade.
    """
    def get_hora_por_indice(indice):
        timedelta_hora = indice * CONSULTA_DURACAO
        return time(timedelta_hora.seconds // 3600, (timedelta_hora.seconds // 60) % 60)
    
    from terapia.models import IntervaloDisponibilidade
    
    segunda_a_domingo(matriz_disponibilidade_booleanos)

    disponibilidade = []
    m = matriz_disponibilidade_booleanos

    i = j = 0
    while i < len(m):
        while j < len(m[i]):
            if m[i][j]:
                hora_inicio = get_hora_por_indice(j)
                dia_semana_inicio_iso = i + 1

                while m[i][j]:
                    if j < len(m[i]) - 1:
                        j += 1
                    else:
                        i += 1
                        if i >= len(m):
                            break
                        j = 0

                j = j if j < NUMERO_PERIODOS_POR_DIA - 1 else 0
                hora_fim = get_hora_por_indice(j)
                dia_semana_fim_iso = i + 1
                fuso_atual = timezone.get_current_timezone()

                intervalo = IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
                    dia_semana_inicio_iso=dia_semana_inicio_iso,
                    hora_inicio=hora_inicio,
                    dia_semana_fim_iso=dia_semana_fim_iso,
                    hora_fim=hora_fim,
                    fuso=fuso_atual,
                )

                disponibilidade.append(intervalo)

            j += 1

            if i >= len(m):
                break

        i += 1
        j = 0

    return disponibilidade


def desprezar_segundos_e_microssegundos(data_hora):
    return data_hora.replace(second=0, microsecond=0)


def converter_dia_semana_iso_com_hora_para_data_hora(dia_semana_iso, hora, fuso):
    """
    Função para converter um par de dia da semana ISO e hora em um objeto datetime.
    Essa conversão é necessária apenas para fazer queries e operações de comparação
    suportadas pelo tipo datetime. Portanto, a data combinada ao dia da semana ISO
    será apenas um "dummy" para que se possa fazer as operações do tipo datetime.

    Segundos e microssegundos são desprezados.
    """
    hora = desprezar_segundos_e_microssegundos(hora)

    data_hora_fuso_original = datetime.combine(
        date(2024, 7, dia_semana_iso),
        hora,
        tzinfo=fuso,
    )

    data_hora_convertida = timezone.localtime(data_hora_fuso_original, UTC)

    return datetime.combine(
        date(2024, 7, data_hora_convertida.isoweekday()),
        data_hora_convertida.time(),
        data_hora_convertida.tzinfo,
    )
