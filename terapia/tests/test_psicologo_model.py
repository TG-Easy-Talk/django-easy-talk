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
from .base_test_case import ModelTestCase
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


class PsicologoModelTest(ModelTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.psicologo_com_agenda_lotada = Psicologo.objects.create(
            usuario=Usuario.objects.create_user(email="psicologo.com.agenda.lotada@example.com", password="senha123"),
            nome_completo='Psicólogo Com Agenda Lotada',
            crp='06/33333',
            valor_consulta=100.00,
        )
        cls.psicologo_com_agenda_lotada.especializacoes.set(cls.especializacoes)
        cls.uma_antecedencia_minima_antes_do_primeiro_agendamento_do_psicologo_com_agenda_lotada = converter_dia_semana_iso_com_hora_para_data_hora(
            dia_semana_iso=1,
            hora=time(0, 0),
            fuso=UTC,
        ) - CONSULTA_ANTECEDENCIA_MINIMA
        cls.criar_disponibilidade_e_ocupar_psicologo_com_agenda_lotada()

    @classmethod
    def criar_disponibilidade_e_ocupar_psicologo_com_agenda_lotada(cls):
        data_hora_inicio = cls.uma_antecedencia_minima_antes_do_primeiro_agendamento_do_psicologo_com_agenda_lotada + CONSULTA_ANTECEDENCIA_MINIMA
        data_hora_fim = data_hora_inicio + CONSULTA_DURACAO
        IntervaloDisponibilidade.objects.criar_por_dia_semana_e_hora(
            dia_semana_inicio_iso=data_hora_inicio.isoweekday(),
            hora_inicio=data_hora_inicio.time(),
            dia_semana_fim_iso=data_hora_fim.isoweekday(),
            hora_fim=data_hora_fim.time(),
            fuso=data_hora_inicio.tzinfo,
            psicologo=cls.psicologo_com_agenda_lotada,
        ),

        with freeze_time(cls.uma_antecedencia_minima_antes_do_primeiro_agendamento_do_psicologo_com_agenda_lotada):
            tempo_decorrido = CONSULTA_ANTECEDENCIA_MINIMA

            while tempo_decorrido <= CONSULTA_ANTECEDENCIA_MAXIMA:
                Consulta.objects.create(
                    data_hora_agendada=data_hora_inicio + tempo_decorrido - CONSULTA_ANTECEDENCIA_MINIMA,
                    paciente=cls.paciente_dummy,
                    psicologo=cls.psicologo_com_agenda_lotada,
                )
                tempo_decorrido += timedelta(weeks=1)

    def test_str_representation(self):
        self.assertEqual(str(self.psicologo_dummy), self.psicologo_dummy.nome_completo)

    def test_get_absolute_url(self):
        url = self.psicologo_dummy.get_absolute_url()
        self.assertEqual(url, reverse('perfil', kwargs={'pk': self.psicologo_dummy.pk}))

    def test_dados_corretos(self):
        self.assertIsNone(self.psicologo_incompleto.sobre_mim)
        self.assertIsNone(self.psicologo_incompleto.valor_consulta)
        self.assertIsNone(self.psicologo_incompleto.foto.name)
        self.assertQuerySetEqual(self.psicologo_incompleto.especializacoes.all(), [], ordered=False)
        self.assertQuerySetEqual(self.psicologo_incompleto.disponibilidade.all(), [], ordered=False)
        self.assertQuerySetEqual(self.psicologo_incompleto.consultas.all(), [], ordered=False)

        usuario = Usuario.objects.create_user(email="psicologo@example.com", password="senha123")
        nome_completo = 'Gabriela Silva'
        crp = '01/99998'
        sobre_mim = 'Psicóloga clínica com 10 anos de experiência.'
        valor_consulta = 100.00
        
        psicologo = Psicologo.objects.create(
            usuario=usuario,
            nome_completo=nome_completo,
            crp=crp,
            sobre_mim=sobre_mim,
            valor_consulta=valor_consulta,
        )
        psicologo.especializacoes.set(self.especializacoes)
        self.set_disponibilidade_generica(psicologo)
        consultas = self.criar_consultas_genericas(self.paciente_dummy, psicologo)

        self.assertEqual(psicologo.nome_completo, nome_completo)
        self.assertEqual(psicologo.crp, crp)
        self.assertEqual(psicologo.usuario, usuario)
        self.assertEqual(psicologo.sobre_mim, sobre_mim)
        self.assertEqual(psicologo.valor_consulta, valor_consulta)
        self.assertIsNone(psicologo.foto.name)
        self.assertQuerySetEqual(psicologo.especializacoes.all(), self.especializacoes, ordered=False)
        self.assertQuerySetEqual(psicologo.disponibilidade.all(), IntervaloDisponibilidade.objects.filter(psicologo=psicologo), ordered=False)
        self.assertQuerySetEqual(psicologo.consultas.all(), consultas, ordered=False)

    def test_fk_usuario_obrigatoria(self):
        with self.assertRaisesMessage(IntegrityError, "NOT NULL"):
            Psicologo.objects.create(
                nome_completo='Psicólogo sem usuário',
                crp='06/19423',
            )

    def test_valor_consulta_invalido(self):
        valores_invalidos = [
            0.00,
            5000.00,
            -100.00,
            19.99,
        ]

        for valor in valores_invalidos:
            with self.subTest(valor=valor):
                with self.assertRaises(ValidationError) as ctx:
                    Psicologo(
                        usuario=self.usuario_dummy,
                        nome_completo='Psicólogo com valor de consulta inválido',
                        crp='01/99997',
                        valor_consulta=valor
                    ).clean_fields()

                self.assertEqual(
                    'valor_consulta_invalido',
                    ctx.exception.error_dict["valor_consulta"][0].code,
                )

    def test_crp_unico(self):
        with self.assertRaisesMessage(IntegrityError, "UNIQUE"):
            Psicologo.objects.create(
                usuario=self.usuario_dummy,
                nome_completo='Maria Souza',
                crp=self.psicologo_dummy.crp,
            )

    def test_crp_invalido(self):
        crps_invalidos = [
            "06-12345",
            "06/123456",
            "06/1234a",
            "06/1234-5",
            "06/1234 5",
            "06 12345",
            "06/1234",
            "06/12345/",
            "06/12345 ",
            "00/12345",
            "00/12345",
            "29/12345",
            "-1/12345",
            "6/12345",
        ]

        for crp in crps_invalidos:
            with self.subTest(crp=crp):
                with self.assertRaises(ValidationError) as ctx:
                    Psicologo(
                        usuario=self.usuario_dummy,
                        nome_completo='Psicólogo com CRP inválido',
                        crp=crp,
                    ).clean_fields()

                self.assertEqual(
                    'crp_invalido',
                    ctx.exception.error_dict["crp"][0].code,
                )

    def test_impede_usuario_com_paciente(self):
        psicologo_em_usuario_com_paciente = Psicologo(
            usuario=self.paciente_dummy.usuario,
            nome_completo='Psicólogo em usuário com paciente',
            crp='06/99999'
        )

        with self.assertRaises(ValidationError) as ctx:
            psicologo_em_usuario_com_paciente.clean_fields()

        self.assertEqual(
            "paciente_ja_relacionado",
            ctx.exception.error_dict["usuario"][0].code,
        )

    def test_impede_usuario_com_outro_psicologo(self):
        psicologo_em_usuario_com_outro_psicologo = Psicologo(
            usuario=self.psicologo_dummy.usuario,
            nome_completo='Psicologo em usuário com, outro psicólogo',
            crp='06/88888',
        )

        with self.assertRaises(ValidationError) as ctx:
            psicologo_em_usuario_com_outro_psicologo.validate_unique()

        self.assertEqual(
            'unique',
            ctx.exception.error_dict['usuario'][0].code
        )

    def test_primeiro_nome(self):
        self.assertEqual(self.psicologo_dummy.primeiro_nome, 'Psicólogo')

    def test_esta_com_perfil_completo(self):
        with self.subTest(psicologo=self.psicologo_completo.nome_completo):    
            self.assertTrue(self.psicologo_completo.esta_com_perfil_completo)

        psicologos_com_perfil_incompleto = {
            "falta_especializacao": Psicologo.objects.create(
                usuario=Usuario.objects.create_user(email='usuario1@example.com', password='senha123'),
                nome_completo='Psicólogo Incompleto',
                crp='05/11112',
                valor_consulta=100.00,
            ),
            "falta_disponibilidade": Psicologo.objects.create(
                usuario=Usuario.objects.create_user(email='usuario2@example.com', password='senha123'),
                nome_completo='Psicólogo Incompleto',
                crp='05/11113',
                valor_consulta=100.00,
            ),
            "falta_valor_consulta": Psicologo.objects.create(
                usuario=Usuario.objects.create_user(email='usuario3@example.com', password='senha123'),
                nome_completo='Psicólogo Incompleto',
                crp='05/11114',
            ),
        }

        for motivo, psicologo in psicologos_com_perfil_incompleto.items():
            if motivo != "falta_especializacao":
                psicologo.especializacoes.set(self.especializacoes)
            if motivo != "falta_disponibilidade":
                self.set_disponibilidade_generica(psicologo)

            with self.subTest(motivo=motivo, psicologo=psicologo.nome_completo):
                self.assertFalse(psicologo.esta_com_perfil_completo)

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
                            self.assertTrue(self.psicologo_completo._tem_intervalo_onde_cabe_uma_consulta_em(data_hora))
                        elif expectativa == "nao_tem_intervalo":
                            self.assertFalse(self.psicologo_completo._tem_intervalo_onde_cabe_uma_consulta_em(data_hora))

                    with self.subTest(data_hora=data_hora):
                        self.assertTrue(self.psicologo_sempre_disponivel._tem_intervalo_onde_cabe_uma_consulta_em(data_hora))

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
                        "intervalos_sobrepostos": [intervalos_do_psicologo[i] for i in range(len(intervalos_do_psicologo))]
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
                                psicologo.get_intervalos_sobrepostos(intervalo["intervalo_que_sobrepoe"]),
                                intervalo["intervalos_sobrepostos"],
                                ordered=False,
                            )
                    elif expectativa == "nao_tem_sobreposicao":
                        with self.subTest(intervalo_que_sobrepoe=intervalo.descrever(), psicologo=psicologo.nome_completo):
                            self.assertIsNone(psicologo.get_intervalos_sobrepostos(intervalo))

        intervalo_qualquer = IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
            3, time(10, 0), 3, time(11, 0), UTC,
        )

        with self.subTest(intervalo=intervalo_qualquer.descrever(), psicologo=self.psicologo_sempre_disponivel.nome_completo):
            self.assertQuerySetEqual(
                self.psicologo_sempre_disponivel.get_intervalos_sobrepostos(intervalo_qualquer),
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
                    datas_hora_ordenadas = self.psicologo_sempre_disponivel._get_datas_hora_dos_intervalos_da_mais_proxima_a_mais_distante_partindo_de(data_hora)
                    
                    with self.subTest(data_hora=data_hora, psicologo=psicologo.nome_completo, datas_hora_ordenadas=datas_hora_ordenadas):
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
        with freeze_time(self.uma_antecedencia_minima_antes_do_primeiro_agendamento_do_psicologo_com_agenda_lotada):
            for fuso in self.fusos_para_teste:
                with timezone.override(fuso), self.subTest(fuso=fuso, psicologo=self.psicologo_com_agenda_lotada.nome_completo):    
                    self.assertIsNone(self.psicologo_com_agenda_lotada.proxima_data_hora_agendavel, "A agenda está lotada")
                    
                    consultas = Consulta.objects.filter(psicologo=self.psicologo_com_agenda_lotada).order_by('data_hora_agendada')
                    consultas.update(estado=EstadoConsulta.CANCELADA)
                    
                    self.assertEqual(
                        self.psicologo_com_agenda_lotada.proxima_data_hora_agendavel,
                        consultas[0].data_hora_agendada,
                        "Todas as consultas foram canceladas, então a próxima data-hora agendável deve ser a da primeira consulta que estava agendada",
                    )
                    
                    consultas.filter(pk=consultas[0].pk).update(estado=EstadoConsulta.SOLICITADA)
                    consultas.filter(pk=consultas[2].pk).update(estado=EstadoConsulta.SOLICITADA)
                    
                    self.assertEqual(
                        self.psicologo_com_agenda_lotada.proxima_data_hora_agendavel,
                        consultas[1].data_hora_agendada,
                        "A primeira e terceira consultas foram solicitadas de novo, então a próxima data-hora agendável deve ser a da segunda consulta que estava agendada",
                    )
                    
                    consultas.filter(pk=consultas[1].pk).update(estado=EstadoConsulta.SOLICITADA)
                    
                    self.assertEqual(
                        self.psicologo_com_agenda_lotada.proxima_data_hora_agendavel,
                        consultas[3].data_hora_agendada,
                        "As primeiras três consultas foram solicitadas de novo, então a próxima data-hora agendável deve ser a da quarta consulta que estava agendada",
                    )

                    for i in range(3, 6):
                        consultas.filter(pk=consultas[i].pk).update(estado=EstadoConsulta.SOLICITADA)
                    
                    self.assertEqual(
                        self.psicologo_com_agenda_lotada.proxima_data_hora_agendavel,
                        consultas[6].data_hora_agendada,
                        "As primeiras seis consultas foram solicitadas de novo, então a próxima data-hora agendável deve ser a da sétima consulta que estava agendada",
                    )

                    consultas.update(estado=EstadoConsulta.SOLICITADA)
                    consultas.filter(pk=consultas.last().pk).update(estado=EstadoConsulta.CANCELADA)

                    self.assertEqual(
                        self.psicologo_com_agenda_lotada.proxima_data_hora_agendavel,
                        consultas.last().data_hora_agendada,
                        "Todas as consultas exceto a última foram solicitadas de novo, então a próxima data-hora agendável deve ser a da última consulta que estava agendada",
                    )

                    consultas.filter(pk=consultas.last().pk).update(estado=EstadoConsulta.SOLICITADA)

        for fuso in self.fusos_para_teste:
            with timezone.override(fuso), self.subTest(fuso=fuso, psicologo=self.psicologo_completo.nome_completo):
                Consulta.objects.filter(psicologo=self.psicologo_completo).delete()
                
                with freeze_time(timezone.localtime(converter_dia_semana_iso_com_hora_para_data_hora(7, time(21, 0), UTC))):
                    self.assertEqual(
                        self.psicologo_completo.proxima_data_hora_agendavel,
                        converter_dia_semana_iso_com_hora_para_data_hora(7, time(22, 0), UTC),
                        "O psicólogo está disponível às 22h de domingo. Como agora são 21h de domingo e a antecedência mínima é de 1 hora, é possível agendar para as 22h.",
                    )

                Consulta.objects.create(
                    data_hora_agendada=converter_dia_semana_iso_com_hora_para_data_hora(7, time(23, 0), UTC),
                    paciente=self.paciente_dummy,
                    psicologo=self.psicologo_completo,
                )

                with freeze_time(timezone.localtime(converter_dia_semana_iso_com_hora_para_data_hora(7, time(21, 30), UTC))):
                    self.assertEqual(
                        self.psicologo_completo.proxima_data_hora_agendavel,
                        converter_dia_semana_iso_com_hora_para_data_hora(1, time(0, 0), UTC) + timedelta(weeks=1),
                        "São 21h30 de domingo. Não é possível agendar às 22h porque é antes da antecedência mínima. 22h30 também não é agendável porque não é um passo de 1 em 1 hora. A próxima data-hora possivelmente agendável é 23h, mas já há consulta nesse horário. Assim, a próxima data-hora agendável é 0h de segunda.",
                    )

                    Consulta.objects.create(
                        data_hora_agendada=converter_dia_semana_iso_com_hora_para_data_hora(1, time(0, 0), UTC) + timedelta(weeks=1),
                        paciente=self.paciente_dummy,
                        psicologo=self.psicologo_completo,
                    )

                    self.assertEqual(
                        self.psicologo_completo.proxima_data_hora_agendavel,
                        converter_dia_semana_iso_com_hora_para_data_hora(1, time(1, 0), UTC) + timedelta(weeks=1),
                        "É o mesmo que o teste anterior, porém 0h de segunda também já está agendado, então a próxima data-hora agendável é 1h de segunda.",
                    )

                    Consulta.objects.create(
                        data_hora_agendada=converter_dia_semana_iso_com_hora_para_data_hora(1, time(1, 0), UTC) + timedelta(weeks=1),
                        paciente=self.paciente_dummy,
                        psicologo=self.psicologo_completo,
                    )

                    for hora in [8, 9, 10, 11, 14, 15, 17]:
                        Consulta.objects.create(
                            data_hora_agendada=converter_dia_semana_iso_com_hora_para_data_hora(1, time(hora, 0), UTC) + timedelta(weeks=1),
                            paciente=self.paciente_dummy,
                            psicologo=self.psicologo_completo,
                        )

                    self.assertEqual(
                        self.psicologo_completo.proxima_data_hora_agendavel,
                        converter_dia_semana_iso_com_hora_para_data_hora(1, time(16, 0), UTC) + timedelta(weeks=1),
                        "É o mesmo que o teste anterior, porém o intervalo de DOM 22h - SEG 2h está cheio, assim como o intervalo de SEG 8h - SEG 12h. O intervalo SEG 14h - SEG 18h está quase cheio, só restando 16h que ainda está disponível. Portanto, a próxima data-hora agendável deve ser SEG 16h.",
                    )

    def test_get_matriz_disponibilidade_booleanos_em_json(self):
        for fuso, matriz_em_json in MATRIZES_DISPONIBILIDADE_GENERICA_BOOLEANOS_EM_JSON.items():
            with timezone.override(fuso), self.subTest(fuso=fuso, psicologo=self.psicologo_completo.nome_completo):
                self.assertEqual(
                    self.psicologo_completo.get_matriz_disponibilidade_booleanos_em_json(),
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
                        self.psicologo_dummy.get_matriz_disponibilidade_booleanos_em_json(),
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
                f"\n[PRÓXIMA DATA-HORA AGENDÁVEL DO PSICÓLOGO: {isoformat_ou_none(psicologo.proxima_data_hora_agendavel)}]"
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
                    esta_agendavel_em = psicologo.esta_agendavel_em(data_hora_local)
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
            proxima_data_hora_agendavel = self.psicologo_completo.proxima_data_hora_agendavel

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
                data_hora_agendada=self.psicologo_completo.proxima_data_hora_agendavel,
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

            proxima_data_hora_agendavel = self.psicologo_sempre_disponivel.proxima_data_hora_agendavel

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
                data_hora=self.psicologo_sempre_disponivel.proxima_data_hora_agendavel,
                psicologo=self.psicologo_sempre_disponivel,
                descricao="Agendar na próxima data-hora agendável",
            )

            fazer_assertions_para_cada_fuso(
                metodo_assertion=self.assertTrue,
                data_hora=self.psicologo_sempre_disponivel.proxima_data_hora_agendavel + timedelta(milliseconds=1),
                psicologo=self.psicologo_sempre_disponivel,
                descricao="Um pouco depois da próxima data-hora agendável",
            )

            with freeze_time(self.uma_antecedencia_minima_antes_do_primeiro_agendamento_do_psicologo_com_agenda_lotada):
                fazer_assertions_para_cada_fuso(
                    metodo_assertion=self.assertFalse,
                    data_hora=self.psicologo_com_agenda_lotada.proxima_data_hora_agendavel,
                    psicologo=self.psicologo_com_agenda_lotada,
                    descricao="O psicólogo está com agenda lotada até a antecedência máxima, não havendo espaço para novas consultas",
                    motivo_para_nao_estar_agendavel=MotivosParaNaoEstarAgendavel.AGENDA_LOTADA,
                )

            with freeze_time(self.uma_antecedencia_minima_antes_do_primeiro_agendamento_do_psicologo_com_agenda_lotada + timedelta(weeks=1)):
                fazer_assertions_para_cada_fuso(
                    metodo_assertion=self.assertTrue,
                    data_hora=self.psicologo_com_agenda_lotada.proxima_data_hora_agendavel,
                    psicologo=self.psicologo_com_agenda_lotada,
                    descricao="Se passou uma semana desde que o psicólogo estava com a agenda lotada, então a antecedência máxima avançou e agora há espaço para um novo agendamento",
                )