from django.test import SimpleTestCase
from terapia.constantes import (
    CONSULTA_DURACAO,
    CONSULTA_DURACAO_MINUTOS,
    NUMERO_PERIODOS_POR_DIA,
    get_consulta_duracao_minutos,
    get_numero_periodos_por_dia,
)
from datetime import timedelta
from unittest.mock import patch
from math import floor


class ConstantesTest(SimpleTestCase):
    """
    Testes para verificar se as constantes atendem às regras necessárias
    para que o sistema funcione.
    """
    def test_consulta_duracao_divisivel_por_um_dia(self):
        self.assertEqual(timedelta(days=1) % CONSULTA_DURACAO, timedelta(0))

    def test_numero_periodos_por_dia_divisivel_por_24(self):
        self.assertEqual((timedelta(days=1) / CONSULTA_DURACAO) % 24, 0)

    def test_numero_periodos_por_dia_maior_ou_igual_a_24(self):
        self.assertGreaterEqual((timedelta(days=1) / CONSULTA_DURACAO), 24)

    def test_consulta_duracao_minutos_inteiro(self):
        self.assertEqual(CONSULTA_DURACAO_MINUTOS, floor(CONSULTA_DURACAO_MINUTOS))

    def test_numero_periodos_por_dia_inteiro(self):
        self.assertEqual(NUMERO_PERIODOS_POR_DIA, floor(NUMERO_PERIODOS_POR_DIA))

    def test_get_numero_periodos_por_dia(self):
        with patch('terapia.constantes.CONSULTA_DURACAO', timedelta(hours=1)):
            self.assertEqual(get_numero_periodos_por_dia(), 24)
        with patch('terapia.constantes.CONSULTA_DURACAO', timedelta(minutes=30)):
            self.assertEqual(get_numero_periodos_por_dia(), 48)
        with patch('terapia.constantes.CONSULTA_DURACAO', timedelta(minutes=15)):
            self.assertEqual(get_numero_periodos_por_dia(), 96)

    def test_get_consulta_duracao_minutos(self):
        with patch('terapia.constantes.CONSULTA_DURACAO', timedelta(hours=1)):
            self.assertEqual(get_consulta_duracao_minutos(), 60)
        with patch('terapia.constantes.CONSULTA_DURACAO', timedelta(minutes=30)):
            self.assertEqual(get_consulta_duracao_minutos(), 30)
        with patch('terapia.constantes.CONSULTA_DURACAO', timedelta(minutes=15)):
            self.assertEqual(get_consulta_duracao_minutos(), 15)
