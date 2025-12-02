from django.db import IntegrityError
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse
from terapia.models import (
    Psicologo,
    IntervaloDisponibilidade,
    Consulta,
    EstadoConsulta,
)
from terapia.service import PsicologoService
from datetime import UTC, datetime, timedelta, time
from django.utils import timezone
import json
from zoneinfo import ZoneInfo
from terapia.constantes import (
    CONSULTA_ANTECEDENCIA_MINIMA,
    CONSULTA_DURACAO,
    CONSULTA_ANTECEDENCIA_MAXIMA,
    NUMERO_PERIODOS_POR_DIA,
)
from terapia.utilidades.geral import (
    converter_dia_semana_iso_com_hora_para_data_hora,
    regra_de_3_numero_periodos_por_dia,
)
from freezegun import freeze_time
from .model_test_case import ModelTestCase
from unittest.mock import patch

Usuario = get_user_model()

n = NUMERO_PERIODOS_POR_DIA
_ = regra_de_3_numero_periodos_por_dia

MATRIZES_DISPONIBILIDADE_GENERICA_BOOLEANOS = {
    UTC: [
        [True] * _(12) + [False] * _(10) + [True] * _(2),
        [True] * _(2) + [False] * _(6) + [True] * _(4) + [False] * _(2) + [True] * _(4) + [False] * _(6),
        [False] * _(8) + [True] * _(4) + [False] * _(2) + [True] * _(4) + [False] * _(6),
        [False] * _(8) + [True] * _(4) + [False] * _(2) + [True] * _(4) + [False] * _(6),
        [False] * _(22) + [True] * _(1) + [False] * _(1),
        [False] * _(1) + [True] * _(2) + [False] * _(21),
        [False] * _(23) + [True] * _(1),
    ],
    ZoneInfo("Etc/GMT+1"): [
        [True] * _(11) + [False] * _(10) + [True] * _(3),
        [True] * _(1) + [False] * _(6) + [True] * _(4) + [False] * _(2) + [True] * _(4) + [False] * _(7),
        [False] * _(7) + [True] * _(4) + [False] * _(2) + [True] * _(4) + [False] * _(7),
        [False] * _(7) + [True] * _(4) + [False] * _(2) + [True] * _(4) + [False] * _(7),
        [False] * _(21) + [True] * _(1) + [False] * _(2),
        [True] * _(2) + [False] * _(22),
        [False] * _(22) + [True] * _(2),
    ],
    ZoneInfo("Etc/GMT+2"): [
        [True] * _(10) + [False] * _(10) + [True] * _(4),
        [False] * _(6) + [True] * _(4) + [False] * _(2) + [True] * _(4) + [False] * _(8),
        [False] * _(6) + [True] * _(4) + [False] * _(2) + [True] * _(4) + [False] * _(8),
        [False] * _(6) + [True] * _(4) + [False] * _(2) + [True] * _(4) + [False] * _(8),
        [False] * _(20) + [True] * _(1) + [False] * _(2) + [True] * _(1),
        [True] * _(1) + [False] * _(23),
        [False] * _(21) + [True] * _(3),
    ],
    ZoneInfo("Etc/GMT-1"): [
        [True] * _(13) + [False] * _(10) + [True] * _(1),
        [True] * _(3) + [False] * _(6) + [True] * _(4) + [False] * _(2) + [True] * _(4) + [False] * _(5),
        [False] * _(9) + [True] * _(4) + [False] * _(2) + [True] * _(4) + [False] * _(5),
        [False] * _(9) + [True] * _(4) + [False] * _(2) + [True] * _(4) + [False] * _(5),
        [False] * _(23) + [True] * _(1),
        [False] * _(2) + [True] * _(2) + [False] * _(20),
        [False] * _(24),
    ],
    ZoneInfo("Etc/GMT-7"): [
        [False] * _(6) + [True] * _(13) + [False] * _(5),
        [False] * _(5) + [True] * _(4) + [False] * _(6) + [True] * _(4) + [False] * _(2) + [True] * _(3),
        [True] * _(1) + [False] * _(14) + [True] * _(4) + [False] * _(2) + [True] * _(3),
        [True] * _(1) + [False] * _(14) + [True] * _(4) + [False] * _(2) + [True] * _(3),
        [True] * _(1) + [False] * _(23),
        [False] * _(5) + [True] * _(1) + [False] * _(2) + [True] * _(2) + [False] * _(14),
        [False] * _(24),
    ],
}

MATRIZES_DISPONIBILIDADE_GENERICA_BOOLEANOS_EM_JSON = {
    fuso: json.dumps(matriz) for fuso, matriz in MATRIZES_DISPONIBILIDADE_GENERICA_BOOLEANOS.items()
}

OUTRAS_MATRIZES_DISPONIBILIDADE_BOOLEANOS = (
    (IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(7, time(23, 0), 1, time(0, 0), UTC), [
        [False] * _(23) + [True] * _(1),
        [False] * _(24),
        [False] * _(24),
        [False] * _(24),
        [False] * _(24),
        [False] * _(24),
        [False] * _(24),
    ]),
    (IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(7, time(23, 0), 1, time(1, 0), UTC), [
        [False] * _(23) + [True] * _(1),
        [True] * _(1) + [False] * _(23),
        [False] * _(24),
        [False] * _(24),
        [False] * _(24),
        [False] * _(24),
        [False] * _(24),
    ]),
    (IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(7, time(22, 0), 2, time(2, 0), UTC), [
        [False] * _(22) + [True] * _(2),
        [True] * _(24),
        [True] * _(2) + [False] * _(22),
        [False] * _(24),
        [False] * _(24),
        [False] * _(24),
        [False] * _(24),
    ]),
    (IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(6, time(22, 0), 2, time(23, 0), UTC), [
        [True] * _(24),
        [True] * _(24),
        [True] * _(23) + [False] * _(1),
        [False] * _(24),
        [False] * _(24),
        [False] * _(24),
        [False] * _(22) + [True] * _(2),
    ]),
    (IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(5, time(22, 0), 2, time(3, 0), UTC), [
        [True] * _(24),
        [True] * _(24),
        [True] * _(3) + [False] * _(21),
        [False] * _(24),
        [False] * _(24),
        [False] * _(22) + [True] * _(2),
        [True] * _(24),
    ]),
    (IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(4, time(22, 0), 3, time(0, 0), UTC), [
        [True] * _(24),
        [True] * _(24),
        [True] * _(24),
        [False] * _(24),
        [False] * _(22) + [True] * _(2),
        [True] * _(24),
        [True] * _(24),
    ]),
    (IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(6, time(13, 0), 5, time(13, 0), UTC), [
        [True] * _(24),
        [True] * _(24),
        [True] * _(24),
        [True] * _(24),
        [True] * _(24),
        [True] * _(13) + [False] * _(11),
        [False] * _(13) + [True] * _(11),
    ]),
    (IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(4, time(0, 0), 4, time(0, 0), UTC), [
        [True] * _(24),
        [True] * _(24),
        [True] * _(24),
        [True] * _(24),
        [True] * _(24),
        [True] * _(24),
        [True] * _(24),
    ]),
    (IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(3, time(10, 0), 3, time(12, 0), UTC), [
        [False] * _(24),
        [False] * _(24),
        [False] * _(24),
        [False] * _(10) + [True] * _(2) + [False] * _(12),
        [False] * _(24),
        [False] * _(24),
        [False] * _(24),
    ]),
    (IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(2, time(12, 0), 2, time(10, 0), UTC), [
        [True] * _(24),
        [True] * _(24),
        [True] * _(10) + [False] * _(2) + [True] * _(12),
        [True] * _(24),
        [True] * _(24),
        [True] * _(24),
        [True] * _(24),
    ]),
)

OUTRAS_MATRIZES_DISPONIBILIDADE_BOOLEANOS_EM_JSON = (
    (intervalo, json.dumps(matriz)) for intervalo, matriz in OUTRAS_MATRIZES_DISPONIBILIDADE_BOOLEANOS
)


class PsicologoServiceTest(ModelTestCase):
    @classmethod
    def criar_psicologo_com_agenda_lotada(cls):
        psicologo_com_agenda_lotada = Psicologo.objects.create(
            usuario=Usuario.objects.create_user(email="psicologo.com.agenda.lotada@example.com", password="senha123"),
            nome_completo='Psicólogo Com Agenda Lotada',
            crp='06/33333',
            valor_consulta=100.00,
        )
        psicologo_com_agenda_lotada.especializacoes.set(cls.especializacoes)
        uma_antecedencia_minima_antes_do_primeiro_agendamento_do_psicologo_com_agenda_lotada = converter_dia_semana_iso_com_hora_para_data_hora(
            dia_semana_iso=1,
            hora=time(0, 0),
            fuso=UTC,
        ) - CONSULTA_ANTECEDENCIA_MINIMA

        data_hora_inicio = uma_antecedencia_minima_antes_do_primeiro_agendamento_do_psicologo_com_agenda_lotada + CONSULTA_ANTECEDENCIA_MINIMA
        data_hora_fim = data_hora_inicio + CONSULTA_DURACAO
        IntervaloDisponibilidade.objects.criar_por_dia_semana_e_hora(
            dia_semana_inicio_iso=data_hora_inicio.isoweekday(),
            hora_inicio=data_hora_inicio.time(),
            dia_semana_fim_iso=data_hora_fim.isoweekday(),
            hora_fim=data_hora_fim.time(),
            fuso=data_hora_inicio.tzinfo,
            psicologo=psicologo_com_agenda_lotada,
        ),

        with freeze_time(uma_antecedencia_minima_antes_do_primeiro_agendamento_do_psicologo_com_agenda_lotada):
            tempo_decorrido = CONSULTA_ANTECEDENCIA_MINIMA

            while tempo_decorrido <= CONSULTA_ANTECEDENCIA_MAXIMA:
                Consulta.objects.create(
                    data_hora_agendada=data_hora_inicio + tempo_decorrido - CONSULTA_ANTECEDENCIA_MINIMA,
                    paciente=cls.paciente_dummy,
                    psicologo=psicologo_com_agenda_lotada,
                )
                tempo_decorrido += timedelta(weeks=1)

        return psicologo_com_agenda_lotada, uma_antecedencia_minima_antes_do_primeiro_agendamento_do_psicologo_com_agenda_lotada


    @patch("terapia.models.CONSULTA_DURACAO", timedelta(hours=1))
    def test_tem_intervalo_onde_cabe_uma_consulta_em(self):
        datas_hora_para_teste = {
            "tem_intervalo": [
                datetime(2024, 8, 7, 11, 0, tzinfo=UTC),
                datetime(2025, 8, 10, 11, 0, tzinfo=UTC),
                datetime(2025, 8, 10, 10, 30, tzinfo=UTC),
                datetime(2025, 8, 14, 22, 00, tzinfo=UTC),
                datetime(2025, 8, 15, 1, 30, tzinfo=UTC),
                datetime(2025, 8, 16, 23, 0, tzinfo=UTC),
                datetime(2025, 8, 16, 23, 30, tzinfo=UTC),
                datetime(2025, 8, 17, 0, 0, tzinfo=UTC),
                datetime(2025, 8, 17, 0, 30, tzinfo=UTC),
            ],
            "nao_tem_intervalo": [
                datetime(2024, 8, 7, 11, 30, tzinfo=UTC),
                datetime(2025, 8, 10, 11, 30, tzinfo=UTC),
                datetime(2025, 8, 10, 12, 0, tzinfo=UTC),
                datetime(2025, 8, 10, 11, 1, tzinfo=UTC),
                datetime(2025, 8, 14, 21, 59, tzinfo=UTC),
                datetime(2025, 8, 14, 22, 1, tzinfo=UTC),
            ],
        }

        for fuso in self.fusos_para_teste:
            for expectativa, datas_hora in datas_hora_para_teste.items():
                for data_hora in datas_hora:
                    data_hora = timezone.localtime(data_hora, fuso)

                    with self.subTest(data_hora=data_hora):
                        if expectativa == "tem_intervalo":
                            self.assertTrue(PsicologoService._tem_intervalo_onde_cabe_uma_consulta_em(self.psicologo_completo, data_hora))
                        elif expectativa == "nao_tem_intervalo":
                            self.assertFalse(
                                PsicologoService._tem_intervalo_onde_cabe_uma_consulta_em(self.psicologo_completo, data_hora))

                    with self.subTest(data_hora=data_hora):
                        self.assertTrue(
                            PsicologoService._tem_intervalo_onde_cabe_uma_consulta_em(self.psicologo_sempre_disponivel, data_hora))

    def test_get_intervalos_sobrepostos(self):
        psicologo = Psicologo.objects.create(
            usuario=Usuario.objects.create_user(email="psicologo@gmail.com", password="senha123"),
            nome_completo='Psicólogo Teste Sobreposição',
            crp='06/11413',
        )

        intervalos_do_psicologo = IntervaloDisponibilidade.objects.bulk_create([
            IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
                7, time(20, 0), 1, time(4, 0), UTC, psicologo,
            ),
            IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
                2, time(10, 0), 2, time(14, 0), UTC, psicologo,
            ),
            IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
                4, time(22, 0), 5, time(2, 0), UTC, psicologo,
            ),
            IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
                6, time(10, 0), 6, time(14, 0), UTC, psicologo,
            ),
        ])

        conjuntos_de_intervalos_para_teste = {
            "com_intervalo_que_vira_a_semana": {
                "tem_sobreposicao": [
                    {
                        "intervalo_que_sobrepoe": IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
                            4, time(21, 59), 5, time(2, 1), UTC,
                        ),
                        "intervalos_sobrepostos": [intervalos_do_psicologo[i] for i in [2]]
                    },
                    {
                        "intervalo_que_sobrepoe": IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
                            2, time(10, 1), 2, time(13, 59), UTC,
                        ),
                        "intervalos_sobrepostos": [intervalos_do_psicologo[i] for i in [1]]
                    },
                    {
                        "intervalo_que_sobrepoe": IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
                            4, time(20, 0), 4, time(22, 0), UTC,
                        ),
                        "intervalos_sobrepostos": [intervalos_do_psicologo[i] for i in [2]]
                    },
                    {
                        "intervalo_que_sobrepoe": IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
                            6, time(14, 0), 6, time(15, 0), UTC,
                        ),
                        "intervalos_sobrepostos": [intervalos_do_psicologo[i] for i in [3]]
                    },
                    {
                        "intervalo_que_sobrepoe": IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
                            4, time(20, 0), 4, time(23, 0), UTC,
                        ),
                        "intervalos_sobrepostos": [intervalos_do_psicologo[i] for i in [2]]
                    },
                    {
                        "intervalo_que_sobrepoe": IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
                            5, time(1, 59), 5, time(3, 0), UTC,
                        ),
                        "intervalos_sobrepostos": [intervalos_do_psicologo[i] for i in [2]]
                    },
                    {
                        "intervalo_que_sobrepoe": IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
                            4, time(22, 0), 5, time(2, 0), UTC,
                        ),
                        "intervalos_sobrepostos": [intervalos_do_psicologo[i] for i in [2]]
                    },
                    {
                        "intervalo_que_sobrepoe": IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
                            3, time(17, 0), 3, time(17, 0), UTC,
                        ),
                        "intervalos_sobrepostos": [intervalos_do_psicologo[i] for i in
                                                   range(len(intervalos_do_psicologo))]
                    },
                    {
                        "intervalo_que_sobrepoe": IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
                            1, time(4, 0), 1, time(5, 0), UTC,
                        ),
                        "intervalos_sobrepostos": [intervalos_do_psicologo[i] for i in [0]]
                    },
                    {
                        "intervalo_que_sobrepoe": IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
                            7, time(1, 0), 7, time(20, 0), UTC,
                        ),
                        "intervalos_sobrepostos": [intervalos_do_psicologo[i] for i in [0]]
                    },
                    {
                        "intervalo_que_sobrepoe": IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
                            7, time(23, 0), 1, time(0, 0), UTC,
                        ),
                        "intervalos_sobrepostos": [intervalos_do_psicologo[i] for i in [0]]
                    },
                    {
                        "intervalo_que_sobrepoe": IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
                            1, time(1, 0), 1, time(2, 0), UTC,
                        ),
                        "intervalos_sobrepostos": [intervalos_do_psicologo[i] for i in [0]]
                    },
                    {
                        "intervalo_que_sobrepoe": IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
                            7, time(22, 0), 7, time(23, 0), UTC,
                        ),
                        "intervalos_sobrepostos": [intervalos_do_psicologo[i] for i in [0]]
                    },
                ],
                "nao_tem_sobreposicao": [
                    IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
                        4, time(20, 0), 4, time(21, 59), UTC,
                    ),
                    IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
                        5, time(2, 30), 5, time(3, 30), UTC,
                    ),
                    IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
                        7, time(18, 0), 7, time(19, 0), UTC,
                    ),
                    IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
                        1, time(4, 1), 2, time(9, 59), UTC,
                    ),
                ],
            },

            "sem_intervalo_que_vira_a_semana": {
                "tem_sobreposicao": [
                    {
                        "intervalo_que_sobrepoe": IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
                            7, time(23, 0), 2, time(10, 0), UTC,
                        ),
                        "intervalos_sobrepostos": [intervalos_do_psicologo[i] for i in [1]]
                    },
                    {
                        "intervalo_que_sobrepoe": IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
                            5, time(2, 0), 4, time(22, 0), UTC,
                        ),
                        "intervalos_sobrepostos": [intervalos_do_psicologo[i] for i in [1, 2, 3]]
                    },
                    {
                        "intervalo_que_sobrepoe": IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
                            5, time(1, 0), 4, time(23, 0), UTC,
                        ),
                        "intervalos_sobrepostos": [intervalos_do_psicologo[i] for i in [1, 2, 3]]
                    },
                    {
                        "intervalo_que_sobrepoe": IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
                            6, time(14, 0), 1, time(0, 0), UTC,
                        ),
                        "intervalos_sobrepostos": [intervalos_do_psicologo[i] for i in [3]]
                    },
                    {
                        "intervalo_que_sobrepoe": IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
                            6, time(14, 0), 2, time(10, 0), UTC,
                        ),
                        "intervalos_sobrepostos": [intervalos_do_psicologo[i] for i in [1, 3]]
                    },
                    {
                        "intervalo_que_sobrepoe": IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
                            6, time(20, 0), 2, time(11, 0), UTC,
                        ),
                        "intervalos_sobrepostos": [intervalos_do_psicologo[i] for i in [1]]
                    },
                    {
                        "intervalo_que_sobrepoe": IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
                            6, time(13, 59), 2, time(9, 59), UTC,
                        ),
                        "intervalos_sobrepostos": [intervalos_do_psicologo[i] for i in [3]]
                    },
                ],
                "nao_tem_sobreposicao": [
                    IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
                        7, time(20, 0), 1, time(4, 0), UTC,
                    ),
                    IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
                        1, time(4, 0), 1, time(5, 0), UTC,
                    ),
                    IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
                        7, time(1, 0), 7, time(20, 0), UTC,
                    ),
                    IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
                        7, time(23, 0), 1, time(0, 0), UTC,
                    ),
                    IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
                        1, time(1, 0), 1, time(2, 0), UTC,
                    ),
                    IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
                        7, time(22, 0), 7, time(23, 0), UTC,
                    ),
                ],
            },

            "sem_nenhum_intervalo": {
                "nao_tem_sobreposicao": [
                    IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
                        7, time(23, 59), 7, time(23, 59), UTC,
                    ),
                    IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
                        1, time(0, 0), 1, time(0, 0), UTC,
                    ),
                    IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
                        1, time(0, 1), 1, time(0, 1), UTC,
                    ),
                ],
            },
        }

        for nome, conjunto in conjuntos_de_intervalos_para_teste.items():
            if nome == "sem_intervalo_que_vira_a_semana":
                psicologo.intervalo_que_vira_a_semana.delete()
            elif nome == "sem_nenhum_intervalo":
                psicologo.disponibilidade.all().delete()

            for expectativa, intervalos in conjunto.items():
                for intervalo in intervalos:
                    if expectativa == "tem_sobreposicao":
                        with self.subTest(
                                intervalo_que_sobrepoe=intervalo["intervalo_que_sobrepoe"].descrever(),
                                intervalos_sobrepostos=intervalo["intervalos_sobrepostos"],
                                psicologo=psicologo.nome_completo
                        ):
                            self.assertQuerySetEqual(
                                PsicologoService.obter_intervalos_sobrepostos(psicologo, intervalo["intervalo_que_sobrepoe"]),
                                intervalo["intervalos_sobrepostos"],
                                ordered=False,
                            )
                    elif expectativa == "nao_tem_sobreposicao":
                        with self.subTest(intervalo_que_sobrepoe=intervalo.descrever(),
                                          psicologo=psicologo.nome_completo):
                            self.assertIsNone(PsicologoService.obter_intervalos_sobrepostos(psicologo, intervalo))

        intervalo_qualquer = IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
            3, time(10, 0), 3, time(11, 0), UTC,
        )

        with self.subTest(intervalo=intervalo_qualquer.descrever(),
                          psicologo=self.psicologo_sempre_disponivel.nome_completo):
            self.assertQuerySetEqual(
                PsicologoService.obter_intervalos_sobrepostos(self.psicologo_sempre_disponivel, intervalo_qualquer),
                self.psicologo_sempre_disponivel.disponibilidade.all(),
                ordered=False
            )

    def test_get_datas_hora_dos_intervalos_da_mais_proxima_a_mais_distante_partindo_de(self):
        datas_hora_para_teste = [dt - CONSULTA_ANTECEDENCIA_MINIMA - CONSULTA_DURACAO for dt in [
            converter_dia_semana_iso_com_hora_para_data_hora(7, time(21, 59), UTC),
            converter_dia_semana_iso_com_hora_para_data_hora(7, time(22, 0), UTC),
            converter_dia_semana_iso_com_hora_para_data_hora(7, time(23, 59), UTC),
            converter_dia_semana_iso_com_hora_para_data_hora(1, time(0, 0), UTC),
            converter_dia_semana_iso_com_hora_para_data_hora(1, time(0, 1), UTC),
            converter_dia_semana_iso_com_hora_para_data_hora(1, time(1, 0), UTC),
            converter_dia_semana_iso_com_hora_para_data_hora(1, time(2, 0), UTC),
            converter_dia_semana_iso_com_hora_para_data_hora(6, time(23, 0), UTC),
            converter_dia_semana_iso_com_hora_para_data_hora(6, time(23, 30), UTC),
            converter_dia_semana_iso_com_hora_para_data_hora(7, time(0, 0), UTC),
            converter_dia_semana_iso_com_hora_para_data_hora(7, time(8, 30), UTC),
            converter_dia_semana_iso_com_hora_para_data_hora(7, time(12, 0), UTC),
            converter_dia_semana_iso_com_hora_para_data_hora(4, time(23, 0), UTC),
            converter_dia_semana_iso_com_hora_para_data_hora(3, time(6, 0), UTC),
            converter_dia_semana_iso_com_hora_para_data_hora(2, time(17, 59), UTC),
            converter_dia_semana_iso_com_hora_para_data_hora(1, time(7, 59), UTC),
            converter_dia_semana_iso_com_hora_para_data_hora(1, time(8, 0), UTC),
            converter_dia_semana_iso_com_hora_para_data_hora(1, time(8, 1), UTC),
            converter_dia_semana_iso_com_hora_para_data_hora(1, time(10, 13), UTC),
            converter_dia_semana_iso_com_hora_para_data_hora(1, time(11, 59), UTC),
            converter_dia_semana_iso_com_hora_para_data_hora(1, time(12, 0), UTC),
            converter_dia_semana_iso_com_hora_para_data_hora(1, time(12, 1), UTC),
        ]] + [
                                    timezone.localtime(),
                                    timezone.now(),
                                ]

        for psicologo in [self.psicologo_completo, self.psicologo_sempre_disponivel]:
            for data_hora in datas_hora_para_teste:
                for fuso in self.fusos_para_teste:
                    data_hora = timezone.localtime(data_hora, fuso)
                    datas_hora_ordenadas = PsicologoService._get_datas_hora_dos_intervalos_da_mais_proxima_a_mais_distante_partindo_de(
                        self.psicologo_sempre_disponivel, data_hora)

                    with self.subTest(data_hora=data_hora, psicologo=psicologo.nome_completo,
                                      datas_hora_ordenadas=datas_hora_ordenadas):
                        self.assertEqual(len(datas_hora_ordenadas), len(set(datas_hora_ordenadas)))

                        for data_hora_atual, data_hora_posterior in zip(datas_hora_ordenadas, datas_hora_ordenadas[1:]):
                            if data_hora_atual > data_hora_posterior:
                                continue

                            self.assertLess(data_hora_atual, data_hora_posterior)

    @patch("terapia.tests.test_psicologo_model.CONSULTA_DURACAO", timedelta(hours=1))
    @patch("terapia.tests.test_psicologo_model.CONSULTA_ANTECEDENCIA_MINIMA", timedelta(hours=1))
    @patch("terapia.tests.test_psicologo_model.CONSULTA_ANTECEDENCIA_MAXIMA", timedelta(days=60))
    @patch("terapia.models.CONSULTA_DURACAO", timedelta(hours=1))
    @patch("terapia.models.CONSULTA_ANTECEDENCIA_MINIMA", timedelta(hours=1))
    @patch("terapia.models.CONSULTA_ANTECEDENCIA_MAXIMA", timedelta(days=60))
    def test_proxima_data_hora_agendavel(self):
        psicologo_com_agenda_lotada, uma_antecedencia_minima_antes_do_primeiro_agendamento_do_psicologo_com_agenda_lotada = self.criar_psicologo_com_agenda_lotada()

        with freeze_time(uma_antecedencia_minima_antes_do_primeiro_agendamento_do_psicologo_com_agenda_lotada):
            for fuso in self.fusos_para_teste:
                with timezone.override(fuso), self.subTest(fuso=fuso,
                                                           psicologo=psicologo_com_agenda_lotada.nome_completo):
                    self.assertIsNone(PsicologoService.obter_proxima_disponibilidade(psicologo_com_agenda_lotada), "A agenda está lotada")

                    consultas = Consulta.objects.filter(psicologo=psicologo_com_agenda_lotada).order_by(
                        'data_hora_agendada')
                    consultas.update(estado=EstadoConsulta.CANCELADA)

                    self.assertEqual(
                        PsicologoService.obter_proxima_disponibilidade(psicologo_com_agenda_lotada),
                        consultas[0].data_hora_agendada,
                        "Todas as consultas foram canceladas, então a próxima data-hora agendável deve ser a da primeira consulta que estava agendada",
                    )

                    consultas.filter(pk=consultas[0].pk).update(estado=EstadoConsulta.SOLICITADA)
                    consultas.filter(pk=consultas[2].pk).update(estado=EstadoConsulta.SOLICITADA)

                    self.assertEqual(
                        PsicologoService.obter_proxima_disponibilidade(psicologo_com_agenda_lotada),
                        consultas[1].data_hora_agendada,
                        "A primeira e terceira consultas foram solicitadas de novo, então a próxima data-hora agendável deve ser a da segunda consulta que estava agendada",
                    )

                    consultas.filter(pk=consultas[1].pk).update(estado=EstadoConsulta.SOLICITADA)

                    self.assertEqual(
                        PsicologoService.obter_proxima_disponibilidade(psicologo_com_agenda_lotada),
                        consultas[3].data_hora_agendada,
                        "As primeiras três consultas foram solicitadas de novo, então a próxima data-hora agendável deve ser a da quarta consulta que estava agendada",
                    )

                    for i in range(3, 6):
                        consultas.filter(pk=consultas[i].pk).update(estado=EstadoConsulta.SOLICITADA)

                    self.assertEqual(
                        PsicologoService.obter_proxima_disponibilidade(psicologo_com_agenda_lotada),
                        consultas[6].data_hora_agendada,
                        "As primeiras seis consultas foram solicitadas de novo, então a próxima data-hora agendável deve ser a da sétima consulta que estava agendada",
                    )

                    consultas.update(estado=EstadoConsulta.SOLICITADA)
                    consultas.filter(pk=consultas.last().pk).update(estado=EstadoConsulta.CANCELADA)

                    self.assertEqual(
                        PsicologoService.obter_proxima_disponibilidade(psicologo_com_agenda_lotada),
                        consultas.last().data_hora_agendada,
                        "Todas as consultas exceto a última foram solicitadas de novo, então a próxima data-hora agendável deve ser a da última consulta que estava agendada",
                    )

                    consultas.filter(pk=consultas.last().pk).update(estado=EstadoConsulta.SOLICITADA)

        for fuso in self.fusos_para_teste:
            with timezone.override(fuso), self.subTest(fuso=fuso, psicologo=self.psicologo_completo.nome_completo):
                Consulta.objects.filter(psicologo=self.psicologo_completo).delete()

                with freeze_time(
                        timezone.localtime(converter_dia_semana_iso_com_hora_para_data_hora(7, time(21, 0), UTC))):
                    self.assertEqual(
                        PsicologoService.obter_proxima_disponibilidade(self.psicologo_completo),
                        converter_dia_semana_iso_com_hora_para_data_hora(7, time(22, 0), UTC),
                        "O psicólogo está disponível às 22h de domingo. Como agora são 21h de domingo e a antecedência mínima é de 1 hora, é possível agendar para as 22h.",
                    )

                Consulta.objects.create(
                    data_hora_agendada=converter_dia_semana_iso_com_hora_para_data_hora(7, time(23, 0), UTC),
                    paciente=self.paciente_dummy,
                    psicologo=self.psicologo_completo,
                )

                with freeze_time(
                        timezone.localtime(converter_dia_semana_iso_com_hora_para_data_hora(7, time(21, 30), UTC))):
                    self.assertEqual(
                        PsicologoService.obter_proxima_disponibilidade(self.psicologo_completo),
                        converter_dia_semana_iso_com_hora_para_data_hora(1, time(0, 0), UTC) + timedelta(weeks=1),
                        "São 21h30 de domingo. Não é possível agendar às 22h porque é antes da antecedência mínima. 22h30 também não é agendável porque não é um passo de 1 em 1 hora. A próxima data-hora possivelmente agendável é 23h, mas já há consulta nesse horário. Assim, a próxima data-hora agendável é 0h de segunda.",
                    )

                    Consulta.objects.create(
                        data_hora_agendada=converter_dia_semana_iso_com_hora_para_data_hora(1, time(0, 0),
                                                                                            UTC) + timedelta(weeks=1),
                        paciente=self.paciente_dummy,
                        psicologo=self.psicologo_completo,
                    )

                    self.assertEqual(
                        PsicologoService.obter_proxima_disponibilidade(self.psicologo_completo),
                        converter_dia_semana_iso_com_hora_para_data_hora(1, time(1, 0), UTC) + timedelta(weeks=1),
                        "É o mesmo que o teste anterior, porém 0h de segunda também já está agendado, então a próxima data-hora agendável é 1h de segunda.",
                    )

                    Consulta.objects.create(
                        data_hora_agendada=converter_dia_semana_iso_com_hora_para_data_hora(1, time(1, 0),
                                                                                            UTC) + timedelta(weeks=1),
                        paciente=self.paciente_dummy,
                        psicologo=self.psicologo_completo,
                    )

                    for hora in [8, 9, 10, 11, 14, 15, 17]:
                        Consulta.objects.create(
                            data_hora_agendada=converter_dia_semana_iso_com_hora_para_data_hora(1, time(hora, 0),
                                                                                                UTC) + timedelta(
                                weeks=1),
                            paciente=self.paciente_dummy,
                            psicologo=self.psicologo_completo,
                        )

                    self.assertEqual(
                        PsicologoService.obter_proxima_disponibilidade(self.psicologo_completo),
                        converter_dia_semana_iso_com_hora_para_data_hora(1, time(16, 0), UTC) + timedelta(weeks=1),
                        "É o mesmo que o teste anterior, porém o intervalo de DOM 22h - SEG 2h está cheio, assim como o intervalo de SEG 8h - SEG 12h. O intervalo SEG 14h - SEG 18h está quase cheio, só restando 16h que ainda está disponível. Portanto, a próxima data-hora agendável deve ser SEG 16h.",
                    )

    def test_get_matriz_disponibilidade_booleanos_em_json(self):
        for fuso, matriz_em_json in MATRIZES_DISPONIBILIDADE_GENERICA_BOOLEANOS_EM_JSON.items():
            with timezone.override(fuso), self.subTest(fuso=fuso, psicologo=self.psicologo_completo.nome_completo):
                self.assertEqual(
                    PsicologoService.gerar_matriz_disponibilidade(self.psicologo_completo),
                    matriz_em_json,
                )

        fuso = UTC

        with timezone.override(fuso):
            for intervalo, matriz in OUTRAS_MATRIZES_DISPONIBILIDADE_BOOLEANOS_EM_JSON:
                self.psicologo_dummy.disponibilidade.all().delete()
                intervalo.psicologo = self.psicologo_dummy
                intervalo.save()

                with self.subTest(fuso=fuso, intervalo=intervalo.descrever()):
                    self.assertEqual(
                        PsicologoService.gerar_matriz_disponibilidade(self.psicologo_dummy),
                        matriz,
                    )

    def test_esta_agendavel_em(self):
        class MotivosParaNaoEstarAgendavel:
            PASSADO = "Não é possível estar agendável no passado"
            ANTECEDENCIA_MUITO_PEQUENA = "Não é possível estar agendável com uma antecedência menor que a permitida"
            ANTECEDENCIA_MUITO_GRANDE = "Não é possível estar agendável com uma antecedência maior que a permitida"
            ANTES_DA_PROXIMA_DATA_HORA_AGENDAVEL = "Não é possível estar agendável antes da próxima data-hora agendável"
            NAO_HA_INTERVALO = "Não é possível estar agendável se não houver intervalo no qual a consulta se encaixe"
            JA_HA_CONSULTA = "Não é possível estar agendável se já houver consulta que toma o tempo da que se deseja agendar"
            AGENDA_LOTADA = "Não é possível estar agendável se o psicólogo estiver com a agenda lotada até a antecedência máxima"

        def isoformat_ou_none(data_hora):
            return data_hora.isoformat() if data_hora is not None else "N/A"

        def formatar_msg_assertion(*,
                                   metodo_assertion,
                                   fuso,
                                   data_hora_original,
                                   data_hora_local,
                                   psicologo,
                                   descricao,
                                   motivo_para_nao_estar_agendavel,
                                   ):
            msg = (
                f"\n[DESCRIÇÃO DO TESTE: {descricao}]"
                f"\n[FUSO: {fuso}]"
                f"\n[DATA-HORA ORIGINAL: {isoformat_ou_none(data_hora_original)}]"
                f"\n[DATA-HORA NO FUSO: {isoformat_ou_none(data_hora_local)}]"
                f"\n[PSICÓLOGO: {psicologo.nome_completo}]"
                f"\n[DEVERIA ESTAR AGENDÁVEL? {"Sim" if metodo_assertion.__func__ is self.assertTrue.__func__ else "Não"}]"
                f"\n[PRÓXIMA DATA-HORA AGENDÁVEL DO PSICÓLOGO: {isoformat_ou_none(PsicologoService.obter_proxima_disponibilidade(psicologo))}]"
            )

            if metodo_assertion.__func__ is self.assertFalse.__func__:
                msg += f"\n[MOTIVO PARA NÃO ESTAR AGENDÁVEL: {motivo_para_nao_estar_agendavel}]"

            return msg

        def fazer_assertions_para_cada_fuso(*,
                                            metodo_assertion,
                                            data_hora,
                                            psicologo,
                                            motivo_para_nao_estar_agendavel="",
                                            descricao,
                                            ):
            for fuso in self.fusos_para_teste:
                data_hora_local = timezone.localtime(data_hora, fuso)

                with self.subTest(agora=agora, data_hora=data_hora_local, psicologo=psicologo.nome_completo):
                    esta_agendavel_em = PsicologoService.verificar_disponibilidade(psicologo, data_hora_local)
                    msg = formatar_msg_assertion(
                        metodo_assertion=metodo_assertion,
                        fuso=fuso,
                        data_hora_original=data_hora,
                        data_hora_local=data_hora_local,
                        psicologo=psicologo,
                        descricao=descricao,
                        motivo_para_nao_estar_agendavel=motivo_para_nao_estar_agendavel,
                    )
                    metodo_assertion(esta_agendavel_em, msg)

        agora = timezone.localtime()

        with freeze_time(agora):
            proxima_data_hora_agendavel = PsicologoService.obter_proxima_disponibilidade(self.psicologo_completo)

            fazer_assertions_para_cada_fuso(
                metodo_assertion=self.assertFalse,
                data_hora=agora - timedelta(minutes=1),
                psicologo=self.psicologo_completo,
                motivo_para_nao_estar_agendavel=MotivosParaNaoEstarAgendavel.PASSADO,
                descricao="Data-hora no passado",
            )

            fazer_assertions_para_cada_fuso(
                metodo_assertion=self.assertFalse,
                data_hora=agora + CONSULTA_ANTECEDENCIA_MINIMA - timedelta(milliseconds=1),
                psicologo=self.psicologo_completo,
                motivo_para_nao_estar_agendavel=MotivosParaNaoEstarAgendavel.ANTECEDENCIA_MUITO_PEQUENA,
                descricao="Um pouco antes do mínimo de antecedência",
            )

            fazer_assertions_para_cada_fuso(
                metodo_assertion=self.assertFalse,
                data_hora=agora + CONSULTA_ANTECEDENCIA_MAXIMA + timedelta(milliseconds=1),
                psicologo=self.psicologo_completo,
                motivo_para_nao_estar_agendavel=MotivosParaNaoEstarAgendavel.ANTECEDENCIA_MUITO_GRANDE,
                descricao="Um pouco depois do máximo de antecedência",
            )

            fazer_assertions_para_cada_fuso(
                metodo_assertion=self.assertFalse,
                data_hora=proxima_data_hora_agendavel + CONSULTA_ANTECEDENCIA_MAXIMA,
                psicologo=self.psicologo_completo,
                motivo_para_nao_estar_agendavel=MotivosParaNaoEstarAgendavel.ANTECEDENCIA_MUITO_GRANDE,
                descricao="Próxima data-hora agendável + máximo de antecedência",
            )

            fazer_assertions_para_cada_fuso(
                metodo_assertion=self.assertFalse,
                data_hora=proxima_data_hora_agendavel - timedelta(milliseconds=1),
                psicologo=self.psicologo_completo,
                motivo_para_nao_estar_agendavel=MotivosParaNaoEstarAgendavel.ANTES_DA_PROXIMA_DATA_HORA_AGENDAVEL,
                descricao="Um pouco antes da próxima data-hora agendável",
            )

            intervalos_do_psicologo = self.psicologo_completo.disponibilidade.all()
            intervalo = intervalos_do_psicologo.first()
            fuso_intervalo = intervalo.data_hora_inicio.tzinfo
            data_intervalo = intervalo.data_hora_inicio.date()
            agora_fuso_intervalo = timezone.localtime(agora, fuso_intervalo)
            diferenca_dias_semana = data_intervalo.isoweekday() - agora_fuso_intervalo.isoweekday()
            diferenca_dias_semana = diferenca_dias_semana + 7 if diferenca_dias_semana <= 0 else diferenca_dias_semana

            data_hora_inicio = datetime.combine(
                agora_fuso_intervalo.date(),
                intervalo.data_hora_inicio.time(),
                fuso_intervalo,
            ) + timedelta(days=diferenca_dias_semana)

            fazer_assertions_para_cada_fuso(
                metodo_assertion=self.assertTrue,
                data_hora=data_hora_inicio,
                psicologo=self.psicologo_completo,
                descricao="Cálculo de uma data-hora de início válida a partir de um intervalo existente do psicólogo",
            )

            intervalo.delete()

            fazer_assertions_para_cada_fuso(
                metodo_assertion=self.assertFalse,
                data_hora=data_hora_inicio,
                psicologo=self.psicologo_completo,
                motivo_para_nao_estar_agendavel=MotivosParaNaoEstarAgendavel.NAO_HA_INTERVALO,
                descricao="Agendar na data-hora anterior não será possível porque o intervalo acabou de ser deletado",
            )

            intervalos_do_psicologo.delete()

            fazer_assertions_para_cada_fuso(
                metodo_assertion=self.assertFalse,
                data_hora=proxima_data_hora_agendavel,
                psicologo=self.psicologo_completo,
                motivo_para_nao_estar_agendavel=MotivosParaNaoEstarAgendavel.NAO_HA_INTERVALO,
                descricao="Não é possível agendar na próxima data-hora agendável pois todos os intervalos do psicólogo foram deletados",
            )

            self.set_disponibilidade_generica(self.psicologo_completo)

            fazer_assertions_para_cada_fuso(
                metodo_assertion=self.assertTrue,
                data_hora=proxima_data_hora_agendavel,
                psicologo=self.psicologo_completo,
                descricao="Os intervalos do psicólogo foram readicionados, permitindo agendamento na próxima data-hora agendável",
            )

            consulta = Consulta.objects.create(
                data_hora_agendada=PsicologoService.obter_proxima_disponibilidade(self.psicologo_completo),
                paciente=self.paciente_dummy,
                psicologo=self.psicologo_completo,
            )

            fazer_assertions_para_cada_fuso(
                metodo_assertion=self.assertFalse,
                data_hora=proxima_data_hora_agendavel,
                psicologo=self.psicologo_completo,
                motivo_para_nao_estar_agendavel=MotivosParaNaoEstarAgendavel.JA_HA_CONSULTA,
                descricao="Uma consulta foi criada na próxima data-hora agendável, então não se pode agendar nessa mesma data-hora de novo",
            )

            fazer_assertions_para_cada_fuso(
                metodo_assertion=self.assertFalse,
                data_hora=proxima_data_hora_agendavel + CONSULTA_DURACAO - timedelta(milliseconds=1),
                psicologo=self.psicologo_completo,
                motivo_para_nao_estar_agendavel=MotivosParaNaoEstarAgendavel.JA_HA_CONSULTA,
                descricao="Um pouco antes do término de uma consulta já agendada",
            )

            fazer_assertions_para_cada_fuso(
                metodo_assertion=self.assertFalse,
                data_hora=proxima_data_hora_agendavel + timedelta(milliseconds=1),
                psicologo=self.psicologo_completo,
                motivo_para_nao_estar_agendavel=MotivosParaNaoEstarAgendavel.JA_HA_CONSULTA,
                descricao="Um pouco depois do início de uma consulta já agendada",
            )

            consulta.estado = EstadoConsulta.CANCELADA
            consulta.save()

            fazer_assertions_para_cada_fuso(
                metodo_assertion=self.assertTrue,
                data_hora=proxima_data_hora_agendavel,
                psicologo=self.psicologo_completo,
                descricao="A consulta que estava marcada para essa data-hora foi cancelada, permitindo um novo agendamento",
            )

            proxima_data_hora_agendavel = PsicologoService.obter_proxima_disponibilidade(self.psicologo_sempre_disponivel)

            fazer_assertions_para_cada_fuso(
                metodo_assertion=self.assertFalse,
                data_hora=agora - timedelta(minutes=1),
                psicologo=self.psicologo_sempre_disponivel,
                motivo_para_nao_estar_agendavel=MotivosParaNaoEstarAgendavel.PASSADO,
                descricao="Data-hora no passado",
            )

            fazer_assertions_para_cada_fuso(
                metodo_assertion=self.assertFalse,
                data_hora=agora,
                psicologo=self.psicologo_sempre_disponivel,
                motivo_para_nao_estar_agendavel=MotivosParaNaoEstarAgendavel.ANTECEDENCIA_MUITO_PEQUENA,
                descricao="Agendar no instante de agora não atende a antecedência mínima",
            )

            fazer_assertions_para_cada_fuso(
                metodo_assertion=self.assertFalse,
                data_hora=agora + timedelta(minutes=1),
                psicologo=self.psicologo_sempre_disponivel,
                motivo_para_nao_estar_agendavel=MotivosParaNaoEstarAgendavel.ANTECEDENCIA_MUITO_PEQUENA,
                descricao="Agendar um minuto depois do instante atual não atende a antecedência mínima",
            )

            fazer_assertions_para_cada_fuso(
                metodo_assertion=self.assertFalse,
                data_hora=agora + CONSULTA_ANTECEDENCIA_MAXIMA + timedelta(milliseconds=1),
                psicologo=self.psicologo_sempre_disponivel,
                motivo_para_nao_estar_agendavel=MotivosParaNaoEstarAgendavel.ANTECEDENCIA_MUITO_GRANDE,
                descricao="Um pouco depois do limite máximo de antecedência",
            )

            fazer_assertions_para_cada_fuso(
                metodo_assertion=self.assertTrue,
                data_hora=agora + CONSULTA_ANTECEDENCIA_MAXIMA,
                psicologo=self.psicologo_sempre_disponivel,
                descricao="Exatamente no limite máximo de antecedência",
            )

            fazer_assertions_para_cada_fuso(
                metodo_assertion=self.assertTrue,
                data_hora=agora + CONSULTA_ANTECEDENCIA_MAXIMA - timedelta(milliseconds=1),
                psicologo=self.psicologo_sempre_disponivel,
                descricao="Um pouco antes do limite máximo de antecedência",
            )

            fazer_assertions_para_cada_fuso(
                metodo_assertion=self.assertTrue,
                data_hora=PsicologoService.obter_proxima_disponibilidade(self.psicologo_sempre_disponivel),
                psicologo=self.psicologo_sempre_disponivel,
                descricao="Agendar na próxima data-hora agendável",
            )

            fazer_assertions_para_cada_fuso(
                metodo_assertion=self.assertTrue,
                data_hora=PsicologoService.obter_proxima_disponibilidade(self.psicologo_sempre_disponivel) + timedelta(milliseconds=1),
                psicologo=self.psicologo_sempre_disponivel,
                descricao="Um pouco depois da próxima data-hora agendável",
            )

            psicologo_com_agenda_lotada, uma_antecedencia_minima_antes_do_primeiro_agendamento_do_psicologo_com_agenda_lotada = self.criar_psicologo_com_agenda_lotada()

            with freeze_time(uma_antecedencia_minima_antes_do_primeiro_agendamento_do_psicologo_com_agenda_lotada):
                fazer_assertions_para_cada_fuso(
                    metodo_assertion=self.assertFalse,
                    data_hora=PsicologoService.obter_proxima_disponibilidade(psicologo_com_agenda_lotada),
                    psicologo=psicologo_com_agenda_lotada,
                    descricao="O psicólogo está com agenda lotada até a antecedência máxima, não havendo espaço para novas consultas",
                    motivo_para_nao_estar_agendavel=MotivosParaNaoEstarAgendavel.AGENDA_LOTADA,
                )

            with freeze_time(
                    uma_antecedencia_minima_antes_do_primeiro_agendamento_do_psicologo_com_agenda_lotada + timedelta(
                            weeks=1)):
                fazer_assertions_para_cada_fuso(
                    metodo_assertion=self.assertTrue,
                    data_hora=PsicologoService.obter_proxima_disponibilidade(psicologo_com_agenda_lotada),
                    psicologo=psicologo_com_agenda_lotada,
                    descricao="Se passou uma semana desde que o psicólogo estava com a agenda lotada, então a antecedência máxima avançou e agora há espaço para um novo agendamento",
                )