from django.forms import ValidationError
from terapia.models import IntervaloDisponibilidade
from terapia.utilidades.geral import converter_dia_semana_iso_com_hora_para_data_hora
from datetime import UTC, datetime, time, timedelta
from terapia.constantes import CONSULTA_DURACAO
from django.utils import timezone
from .model_test_case import ModelTestCase
from .test_psicologo_model import (
    MATRIZES_DISPONIBILIDADE_GENERICA_BOOLEANOS_EM_JSON,
    OUTRAS_MATRIZES_DISPONIBILIDADE_BOOLEANOS_EM_JSON,
)


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

    def test_datas_hora_divisiveis_por_duracao_consulta(self):
        with self.assertRaises(ValidationError) as ctx:
            IntervaloDisponibilidade(
                data_hora_inicio=self.data_hora_nao_divisivel_por_duracao_consulta,
                data_hora_fim=self.data_hora_nao_divisivel_por_duracao_consulta + CONSULTA_DURACAO,
                psicologo=self.psicologo_dummy,
            ).clean_fields()

        self.assertEqual("data_hora_nao_divisivel_por_duracao_consulta", ctx.exception.error_dict["data_hora_inicio"][0].code)
        self.assertEqual("data_hora_nao_divisivel_por_duracao_consulta", ctx.exception.error_dict["data_hora_fim"][0].code)

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

    def test_get_datas_hora(self):
        intervalos_para_teste = [
            IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
                1, time(0, 0), 1, time(1, 0), UTC,
            ),
            IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
                1, time(1, 0), 1, time(0, 0), UTC,
            ),
            IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
                1, time(0, 0), 7, time(23, 0), UTC,
            ),
            IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
                7, time(23, 0), 1, time(0, 0), UTC,
            ),
            IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
                7, time(23, 0), 1, time(1, 0), UTC,
            ),
        ] + list(self.psicologo_completo.disponibilidade.all()) + list(self.psicologo_sempre_disponivel.disponibilidade.all())

        for intervalo in intervalos_para_teste:
            datas_hora = list(intervalo.get_datas_hora())

            self.assertGreater(len(datas_hora), 0)
            self.assertEqual(datas_hora[0], intervalo.data_hora_inicio)

            uma_consulta_antes_do_fim = intervalo.data_hora_fim - CONSULTA_DURACAO
            uma_consulta_antes_do_fim = converter_dia_semana_iso_com_hora_para_data_hora(
                uma_consulta_antes_do_fim.isoweekday(),
                uma_consulta_antes_do_fim.time(),
                uma_consulta_antes_do_fim.tzinfo,
            )

            self.assertEqual(datas_hora[-1], uma_consulta_antes_do_fim)

            total_datas_hora_esperado = intervalo.duracao / CONSULTA_DURACAO

            self.assertEqual(len(datas_hora), total_datas_hora_esperado)

            for i in range(len(datas_hora) - 1):
                diferenca = datas_hora[i + 1] - datas_hora[i]

                if datas_hora[i + 1] <= datas_hora[i]:
                    diferenca += timezone.timedelta(weeks=1)

                self.assertEqual(
                    diferenca,
                    CONSULTA_DURACAO,
                )

    def test_tem_as_mesmas_datas_hora_que(self):
        outro_intervalo_de_semana_completa = IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
            7, time(23, 59), 7, time(23, 59), UTC,
        )

        with self.subTest(
            intervalo_1=str(self.intervalo_de_semana_completa),
            intervalo_2=str(outro_intervalo_de_semana_completa),
        ):
            self.assertTrue(self.intervalo_de_semana_completa.tem_as_mesmas_datas_hora_que(outro_intervalo_de_semana_completa))

        data_hora_inicio = converter_dia_semana_iso_com_hora_para_data_hora(1, time(0, 0), UTC)
        data_hora_fim = converter_dia_semana_iso_com_hora_para_data_hora(7, time(23, 59), UTC)

        intervalo = IntervaloDisponibilidade.objects.criar_por_dia_semana_e_hora(
            data_hora_inicio.isoweekday(),
            data_hora_inicio.time(),
            data_hora_fim.isoweekday(),
            data_hora_fim.time(),
            data_hora_inicio.tzinfo,
            self.psicologo_dummy,
        )

        for fuso in self.fusos_para_teste:
            data_hora_inicio_convertida = timezone.localtime(data_hora_inicio, fuso)
            data_hora_fim_convertida = timezone.localtime(data_hora_fim, fuso)
            intervalo_igual = IntervaloDisponibilidade.objects.criar_por_dia_semana_e_hora(
                data_hora_inicio_convertida.isoweekday(),
                data_hora_inicio_convertida.time(),
                data_hora_fim_convertida.isoweekday(),
                data_hora_fim_convertida.time(),
                fuso,
                self.psicologos_dummies[1],
            )

            with self.subTest(
                intervalo_1=str(intervalo),
                intervalo_2=str(intervalo_igual),
            ):
                self.assertTrue(intervalo.tem_as_mesmas_datas_hora_que(intervalo_igual))

            data_hora_inicio_convertida_diferente = data_hora_inicio_convertida - timedelta(minutes=1)
            intervalo_com_data_hora_inicio_diferente = IntervaloDisponibilidade.objects.criar_por_dia_semana_e_hora(
                data_hora_inicio_convertida_diferente.isoweekday(),
                data_hora_inicio_convertida_diferente.time(),
                data_hora_fim_convertida.isoweekday(),
                data_hora_fim_convertida.time(),
                fuso,
                self.psicologos_dummies[1],
            )

            with self.subTest(
                intervalo_1=str(intervalo),
                intervalo_2=str(intervalo_com_data_hora_inicio_diferente),
            ):
                self.assertFalse(intervalo.tem_as_mesmas_datas_hora_que(intervalo_com_data_hora_inicio_diferente))

            data_hora_fim_convertida_diferente = data_hora_fim_convertida + timedelta(minutes=1)
            intervalo_com_data_hora_fim_diferente = IntervaloDisponibilidade.objects.criar_por_dia_semana_e_hora(
                data_hora_inicio_convertida.isoweekday(),
                data_hora_inicio_convertida.time(),
                data_hora_fim_convertida_diferente.isoweekday(),
                data_hora_fim_convertida_diferente.time(),
                fuso,
                self.psicologos_dummies[1],
            )

            with self.subTest(
                intervalo_1=str(intervalo),
                intervalo_2=str(intervalo_com_data_hora_fim_diferente),
            ):
                self.assertFalse(intervalo.tem_as_mesmas_datas_hora_que(intervalo_com_data_hora_fim_diferente))

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

                            with self.subTest(data_hora=data_hora, intervalo=str(intervalo)):
                                if expectativa == "contem":
                                    self.assertTrue(data_hora in intervalo)
                                elif expectativa == "nao_contem":
                                    self.assertFalse(data_hora in intervalo)

    def test_from_matriz(self):
        for fuso, matriz in MATRIZES_DISPONIBILIDADE_GENERICA_BOOLEANOS_EM_JSON.items():
            with timezone.override(fuso):    
                intervalos = IntervaloDisponibilidade.from_matriz(matriz)

            with self.subTest(fuso=fuso, matriz=matriz):
                self.assertEqual(len(intervalos), len(self.get_disponibilidade_generica()))

                tem_algum_intervalo_com_as_mesmas_datas_hora = False

                for intervalo in intervalos:
                    for outro_intervalo in self.get_disponibilidade_generica():
                        if intervalo.tem_as_mesmas_datas_hora_que(outro_intervalo):
                            tem_algum_intervalo_com_as_mesmas_datas_hora = True
                            break
                
                with self.subTest(intervalo=str(intervalo)):
                    self.assertTrue(tem_algum_intervalo_com_as_mesmas_datas_hora)

        for intervalo, matriz in OUTRAS_MATRIZES_DISPONIBILIDADE_BOOLEANOS_EM_JSON:
            intervalos = IntervaloDisponibilidade.from_matriz(matriz)

            with self.subTest(intervalo=str(intervalo), matriz=matriz):
                self.assertEqual(len(intervalos), 1)
                self.assertEqual(intervalos[0], intervalo)
