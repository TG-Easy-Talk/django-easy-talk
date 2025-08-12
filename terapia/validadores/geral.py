from terapia.constantes import MULTIPLO_CONSULTA_DURACAO_MINUTOS

def is_multiplo_da_duracao_de_consulta(hora):
    return hora.minute % MULTIPLO_CONSULTA_DURACAO_MINUTOS != 0