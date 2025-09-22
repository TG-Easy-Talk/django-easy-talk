from datetime import timedelta


def get_consulta_duracao_minutos():
    return CONSULTA_DURACAO.total_seconds() / 60


def get_numero_periodos_por_dia():
    return timedelta(days=1) / CONSULTA_DURACAO


CONSULTA_ANTECEDENCIA_MINIMA = timedelta(hours=1)
CONSULTA_ANTECEDENCIA_MAXIMA = timedelta(days=60)
CONSULTA_DURACAO = timedelta(hours=1)
CONSULTA_DURACAO_MINUTOS = int(get_consulta_duracao_minutos())
NUMERO_PERIODOS_POR_DIA = int(get_numero_periodos_por_dia())
