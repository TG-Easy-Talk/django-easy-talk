from datetime import UTC, datetime, time
from unittest.mock import patch
from terapia.utilidades.geral import (
    desprezar_segundos_e_microssegundos,
    converter_dia_semana_iso_com_hora_para_data_hora,
    regra_de_3_numero_periodos_por_dia,
)
from django.utils import timezone
from .base_test_case import BaseTestCase

class UtilidadesTest(BaseTestCase):
    def test_desprezar_segundos_e_microssegundos(self):
        data_hora = datetime(2024, 1, 1, 12, 30, 45, 123456)
        resultado = desprezar_segundos_e_microssegundos(data_hora)
        esperado = datetime(2024, 1, 1, 12, 30)
        self.assertEqual(resultado, esperado)
        self.assertEqual(resultado.second, 0)
        self.assertEqual(resultado.microsecond, 0)
        self.assertEqual(resultado, data_hora.replace(second=0, microsecond=0))

    def test_converter_dia_semana_iso_com_hora_para_data_hora(self):
        dias_semana_iso_com_hora = [
            (7, time(23, 0)),
            (1, time(0, 0)),
            (1, time(1, 0)),
            (3, time(12, 30)),
            (5, time(15, 45)),
        ]

        for fuso in self.fusos_para_teste:
            for dia_semana_iso_com_hora in dias_semana_iso_com_hora:
                dia_semana_iso, hora = dia_semana_iso_com_hora
                data_hora = datetime(2025, 9, dia_semana_iso, hora.hour, hora.minute, tzinfo=UTC)
                data_hora = timezone.localtime(data_hora, fuso)
                resultado = converter_dia_semana_iso_com_hora_para_data_hora(
                    data_hora.isoweekday(), data_hora.time(), data_hora.tzinfo
                )
                
                with self.subTest(dia_semana_iso_com_hora=dia_semana_iso_com_hora, fuso=fuso):
                    self.assertEqual(
                        resultado,
                        datetime(2024, 7, dia_semana_iso, hora.hour, hora.minute, tzinfo=UTC)
                    )
    
    def test_regra_de_3_numero_periodos_por_dia(self):
        valores_n = [i for i in range(25)]
        lista_numero_periodos_por_dia = [24, 48, 96]

        for numero_periodos_por_dia in lista_numero_periodos_por_dia:
            with patch(
                "terapia.utilidades.geral.NUMERO_PERIODOS_POR_DIA",
                numero_periodos_por_dia,
            ):
                for n in valores_n:
                    with self.subTest(numero_periodos_por_dia=numero_periodos_por_dia, n=n):
                        resultado = regra_de_3_numero_periodos_por_dia(n)
                        self.assertEqual(resultado, n * numero_periodos_por_dia // 24)