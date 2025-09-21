from datetime import date, datetime, UTC
from django.utils import timezone
from terapia.constantes import NUMERO_PERIODOS_POR_DIA


def regra_de_3_numero_periodos_por_dia(n):
        """
        Recebe um número "n" que representa um horário num dia de 24 horas e retorna
        o seu correspondente num dia de NUMERO_PERIODOS_POR_DIA horas.

        Exemplo: se n=6 e NUMERO_PERIODOS_POR_DIA=12, então a função retorna 3.
        """
        return int(n * NUMERO_PERIODOS_POR_DIA // 24)


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
