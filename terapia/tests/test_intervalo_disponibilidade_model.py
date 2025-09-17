from django.forms import ValidationError
from django.contrib.auth import get_user_model
from terapia.models import IntervaloDisponibilidade
from terapia.utilidades.geral import converter_dia_semana_iso_com_hora_para_data_hora
from datetime import UTC, datetime, time
from terapia.constantes import CONSULTA_DURACAO
from django.utils import timezone
from .base_test_case import ModelTestCase


Usuario = get_user_model()


class IntervaloDisponibilidadeModelTest(ModelTestCase):
    def test_str_representation(self):
        with timezone.override(UTC):    
            self.assertEqual(str(self.intervalo_de_semana_completa), "Segunda às 00:00:00 até Segunda às 00:00:00 (UTC)")

    def test_dados_corretos(self):
        data_hora_inicio = converter_dia_semana_iso_com_hora_para_data_hora(3, time(12, 0), UTC)
        data_hora_fim = converter_dia_semana_iso_com_hora_para_data_hora(4, time(12, 0), UTC)

        intervalo = IntervaloDisponibilidade.objects.create(
            data_hora_inicio=data_hora_inicio,
            data_hora_fim=data_hora_fim,
            psicologo=self.psicologo_dummy,
        )

        self.assertEqual(intervalo.data_hora_inicio, data_hora_inicio)
        self.assertEqual(intervalo.data_hora_fim, data_hora_fim)
        self.assertEqual(intervalo.psicologo, self.psicologo_dummy)

    def test_impede_sobreposicao_com_outro_intervalo_do_psicologo(self):
        with self.assertRaises(ValidationError) as ctx:
            IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
                1, time(0, 0), 1, time(0, 0), UTC, self.psicologo_completo,
            ).clean()

        self.assertEqual(
            "sobreposicao_intervalos",
            ctx.exception.code,
        )

    def test_impede_data_hora_fora_do_range(self):
        with self.assertRaises(ValidationError) as ctx:
            IntervaloDisponibilidade(
                data_hora_inicio=datetime(2024, 6, 30, 23, 59, tzinfo=UTC),
                data_hora_fim=datetime(2024, 7, 1, 10, 0, tzinfo=UTC),
                psicologo=self.psicologo_dummy,
            ).clean_fields()

        self.assertEqual(
            "intervalo_data_hora_range_invalido",
            ctx.exception.error_dict["data_hora_inicio"][0].code,
        )

        with self.assertRaises(ValidationError) as ctx:
            IntervaloDisponibilidade.objects.create(
                data_hora_inicio=datetime(2024, 7, 7, 20, 0, tzinfo=UTC),
                data_hora_fim=datetime(2024, 7, 8, 0, 1, tzinfo=UTC),
                psicologo=self.psicologo_dummy,
            ).clean_fields()

        self.assertEqual(
            "intervalo_data_hora_range_invalido",
            ctx.exception.error_dict["data_hora_fim"][0].code,
        )

    def test_segundos_e_microssegundos_sao_desprezados(self):
        data_hora_inicio = converter_dia_semana_iso_com_hora_para_data_hora(1, time(0, 0, 30, 59), UTC)
        data_hora_fim = data_hora_inicio + CONSULTA_DURACAO
        
        intervalo = IntervaloDisponibilidade.objects.criar_por_dia_semana_e_hora(
            data_hora_inicio.isoweekday(),
            data_hora_inicio.time(),
            data_hora_fim.isoweekday(),
            data_hora_fim.time(),
            data_hora_inicio.tzinfo,
            self.psicologo_incompleto,
        )
        self.assertEqual(intervalo.data_hora_inicio, data_hora_inicio.replace(second=0, microsecond=0))
        self.assertEqual(intervalo.data_hora_fim, data_hora_fim.replace(second=0, microsecond=0))

    def test_contains(self):
        datas_hora_iguais = [
            converter_dia_semana_iso_com_hora_para_data_hora(3, time(12, 0), UTC),
            converter_dia_semana_iso_com_hora_para_data_hora(6, time(12, 0), UTC),
        ]

        datas_hora_dentro = [
            converter_dia_semana_iso_com_hora_para_data_hora(3, time(12, 1), UTC),
            converter_dia_semana_iso_com_hora_para_data_hora(6, time(11, 59), UTC),
            converter_dia_semana_iso_com_hora_para_data_hora(5, time(6, 0), UTC),
        ]
        
        datas_hora_fora = [
            converter_dia_semana_iso_com_hora_para_data_hora(3, time(11, 59), UTC),
            converter_dia_semana_iso_com_hora_para_data_hora(6, time(12, 1), UTC),
            converter_dia_semana_iso_com_hora_para_data_hora(2, time(12, 0), UTC),
            converter_dia_semana_iso_com_hora_para_data_hora(1, time(0, 0), UTC),
            converter_dia_semana_iso_com_hora_para_data_hora(1, time(0, 1), UTC),
            converter_dia_semana_iso_com_hora_para_data_hora(7, time(23, 59), UTC),
            converter_dia_semana_iso_com_hora_para_data_hora(6, time(20, 0), UTC),
            converter_dia_semana_iso_com_hora_para_data_hora(7, time(10, 0), UTC),
        ]

        testes = [
            {
                "intervalo": IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
                    1, time(0, 0), 1, time(0, 0), UTC,
                ),
                "datas_hora": {
                    "contem": [
                        converter_dia_semana_iso_com_hora_para_data_hora(1, time(0, 0), UTC),
                        converter_dia_semana_iso_com_hora_para_data_hora(1, time(0, 1), UTC),
                        converter_dia_semana_iso_com_hora_para_data_hora(7, time(23, 59), UTC),
                        converter_dia_semana_iso_com_hora_para_data_hora(4, time(12, 0), UTC),
                    ],
                },
            },
            {
                "intervalo": IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
                    3, time(12, 0), 6, time(12, 0), UTC,
                ),
                "datas_hora": {
                    "contem": datas_hora_dentro + datas_hora_iguais,
                    "nao_contem": datas_hora_fora,
                },
            },
            {
                "intervalo": IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
                    6, time(12, 0), 3, time(12, 0), UTC,
                ),
                "datas_hora": {
                    "contem": datas_hora_fora + datas_hora_iguais,
                    "nao_contem": datas_hora_dentro,
                },
            },
        ]

        for fuso in self.fusos_para_teste:
            with timezone.override(fuso):
                for teste in testes:
                    intervalo = teste["intervalo"]

                    for expectativa, datas_hora in teste["datas_hora"].items():
                        for data_hora in datas_hora:
                            data_hora = timezone.localtime(data_hora)

                            with self.subTest(data_hora=data_hora, intervalo=intervalo):
                                if expectativa == "contem":
                                    self.assertTrue(data_hora in intervalo)
                                elif expectativa == "nao_contem":
                                    self.assertFalse(data_hora in intervalo)
