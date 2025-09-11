from django.test import TestCase
from django.contrib.auth import get_user_model
from terapia.models import Psicologo, IntervaloDisponibilidade
from terapia.utilidades.geral import converter_dia_semana_iso_com_hora_para_data_hora
from datetime import UTC, time, timedelta
from terapia.constantes import CONSULTA_DURACAO
from django.utils import timezone
from .constantes import FUSOS_PARA_TESTE


Usuario = get_user_model()


class IntervaloDisponibilidadeModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.psicologo_comum = Psicologo.objects.create(
            usuario=Usuario.objects.create_user(email="psicologo@example.com"),
            nome_completo='Psicólogo Comum',
            crp='01/11111',
        )

        cls.data_hora_inicio = converter_dia_semana_iso_com_hora_para_data_hora(3, time(0, 0), UTC)
        cls.data_hora_fim = cls.data_hora_inicio + (timedelta(days=1.5) // CONSULTA_DURACAO) * CONSULTA_DURACAO

        cls.intervalo = IntervaloDisponibilidade.objects.criar_por_dia_semana_e_hora(
            cls.data_hora_inicio.isoweekday(),
            cls.data_hora_inicio.time(),
            cls.data_hora_fim.isoweekday(),
            cls.data_hora_fim.time(),
            cls.data_hora_inicio.tzinfo,
            cls.psicologo_comum,
        )

        cls.psicologo_dummy = Psicologo.objects.create(
            usuario=Usuario.objects.create_user(email="psicologo.dummy@example.com"),
            nome_completo='Psicólogo Dummy',
            crp='01/11112',
        )

    def test_str_representation(self):
        with timezone.override(UTC):    
            self.assertEqual(str(self.intervalo), "Quarta às 00:00:00 até Quinta às 12:00:00 (UTC)")

    def test_dados_corretos(self):
        self.assertEqual(self.intervalo.data_hora_inicio, self.data_hora_inicio)
        self.assertEqual(self.intervalo.data_hora_fim, self.data_hora_fim)
        self.assertEqual(self.intervalo.psicologo, self.psicologo_comum)

    def test_segundos_e_microssegundos_sao_desprezados(self):
        data_hora_inicio = converter_dia_semana_iso_com_hora_para_data_hora(1, time(0, 0, 30, 59), UTC)
        data_hora_fim = data_hora_inicio + CONSULTA_DURACAO
        
        self.psicologo_dummy.disponibilidade.all().delete()

        intervalo = IntervaloDisponibilidade.objects.criar_por_dia_semana_e_hora(
            data_hora_inicio.isoweekday(),
            data_hora_inicio.time(),
            data_hora_fim.isoweekday(),
            data_hora_fim.time(),
            data_hora_inicio.tzinfo,
            self.psicologo_dummy,
        )
        self.assertEqual(intervalo.data_hora_inicio, data_hora_inicio.replace(second=0, microsecond=0))
        self.assertEqual(intervalo.data_hora_fim, data_hora_fim.replace(second=0, microsecond=0))

    def test_contains(self):
        self.psicologo_dummy.disponibilidade.all().delete()
        
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
            # {
            #     "intervalo": IntervaloDisponibilidade.objects.create(
            #         data_hora_inicio=data_hora_inicio_e_fim,
            #         data_hora_fim=data_hora_inicio_e_fim,
            #         psicologo=self.psicologo_dummy,
            #     ),
            #     "datas_hora": [
            #         converter_dia_semana_iso_com_hora_para_data_hora(1, time(0, 0), UTC),
            #         converter_dia_semana_iso_com_hora_para_data_hora(1, time(0, 1), UTC),
            #         converter_dia_semana_iso_com_hora_para_data_hora(7, time(23, 59), UTC),
            #         converter_dia_semana_iso_com_hora_para_data_hora(4, time(12, 0), UTC),
            #     ],
            # },
            # {
            #     "intervalo": IntervaloDisponibilidade.objects.create(
            #         data_hora_inicio=data_hora_inicio_e_fim,
            #         data_hora_fim=data_hora_inicio_e_fim,
            #         psicologo=self.psicologo_dummy,
            #     ),
            #     "datas_hora": [
            #         converter_dia_semana_iso_com_hora_para_data_hora(1, time(0, 0), UTC),
            #         converter_dia_semana_iso_com_hora_para_data_hora(1, time(0, 1), UTC),
            #         converter_dia_semana_iso_com_hora_para_data_hora(7, time(23, 59), UTC),
            #         converter_dia_semana_iso_com_hora_para_data_hora(4, time(12, 0), UTC),
            #     ],
            # },
        ]

        for fuso in FUSOS_PARA_TESTE:
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
