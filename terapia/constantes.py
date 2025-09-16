from datetime import timedelta


CONSULTA_ANTECEDENCIA_MINIMA = timedelta(hours=1)
CONSULTA_ANTECEDENCIA_MAXIMA = timedelta(days=60)
CONSULTA_DURACAO = timedelta(hours=0.25)
CONSULTA_DURACAO_MINUTOS = int(CONSULTA_DURACAO.total_seconds() // 60)
NUMERO_PERIODOS_POR_DIA = int(timedelta(days=1) // CONSULTA_DURACAO)
