from django.db import IntegrityError
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from terapia.models import (
    Paciente,
    Psicologo,
    Especializacao,
    IntervaloDisponibilidade,
    Consulta,
    EstadoConsulta,
)
from decimal import Decimal
from datetime import UTC, datetime, timedelta, time
from django.utils import timezone
import json
from zoneinfo import ZoneInfo
from terapia.constantes import CONSULTA_ANTECEDENCIA_MINIMA, CONSULTA_DURACAO, CONSULTA_ANTECEDENCIA_MAXIMA
from terapia.utilidades.disponibilidade import converter_dia_semana_iso_com_hora_para_data_hora, get_matriz_disponibilidade_booleanos_em_json
from .constantes import FUSOS_PARA_TESTE


Usuario = get_user_model()


MATRIZES_DISPONIBILIDADE_GENERICA_BOOLEANOS = {
    UTC: [
        [True] * 12 + [False] * 10 + [True] * 2,
        [True] * 2 + [False] * 6 + [True] * 4 + [False] * 2 + [True] * 4 + [False] * 6,
        [False] * 8 + [True] * 4 + [False] * 2 + [True] * 4 + [False] * 6,
        [False] * 8 + [True] * 4 + [False] * 2 + [True] * 4 + [False] * 6,
        [False] * 22 + [True] * 1 + [False] * 1,
        [False] * 1 + [True] * 2 + [False] * 21,
        [False] * 23 + [True] * 1,
    ],
    ZoneInfo("Etc/GMT+1"): [
        [True] * 11 + [False] * 10 + [True] * 3,
        [True] * 1 + [False] * 6 + [True] * 4 + [False] * 2 + [True] * 4 + [False] * 7,
        [False] * 7 + [True] * 4 + [False] * 2 + [True] * 4 + [False] * 7,
        [False] * 7 + [True] * 4 + [False] * 2 + [True] * 4 + [False] * 7,
        [False] * 21 + [True] * 1 + [False] * 2,
        [True] * 2 + [False] * 22,
        [False] * 22 + [True] * 2,
    ],
    ZoneInfo("Etc/GMT+2"): [
        [True] * 10 + [False] * 10 + [True] * 4,
        [False] * 6 + [True] * 4 + [False] * 2 + [True] * 4 + [False] * 8,
        [False] * 6 + [True] * 4 + [False] * 2 + [True] * 4 + [False] * 8,
        [False] * 6 + [True] * 4 + [False] * 2 + [True] * 4 + [False] * 8,
        [False] * 20 + [True] * 1 + [False] * 2 + [True] * 1,
        [True] * 1 + [False] * 23,
        [False] * 21 + [True] * 3,
    ],
    ZoneInfo("Etc/GMT-1"): [
        [True] * 13 + [False] * 10 + [True] * 1,
        [True] * 3 + [False] * 6 + [True] * 4 + [False] * 2 + [True] * 4 + [False] * 5,
        [False] * 9 + [True] * 4 + [False] * 2 + [True] * 4 + [False] * 5,
        [False] * 9 + [True] * 4 + [False] * 2 + [True] * 4 + [False] * 5,
        [False] * 23 + [True] * 1,
        [False] * 2 + [True] * 2 + [False] * 20,
        [False] * 24,
    ],
    ZoneInfo("Etc/GMT-7"): [
        [False] * 6 + [True] * 13 + [False] * 5,
        [False] * 5 + [True] * 4 + [False] * 6 + [True] * 4 + [False] * 2 + [True] * 3,
        [True] * 1 + [False] * 14 + [True] * 4 + [False] * 2 + [True] * 3,
        [True] * 1 + [False] * 14 + [True] * 4 + [False] * 2 + [True] * 3,
        [True] * 1 + [False] * 23,
        [False] * 5 + [True] * 1 + [False] * 2 + [True] * 2 + [False] * 14,
        [False] * 24,
    ],
}

MATRIZES_DISPONIBILIDADE_GENERICA_BOOLEANOS_EM_JSON = {
    fuso: json.dumps(matriz) for fuso, matriz in MATRIZES_DISPONIBILIDADE_GENERICA_BOOLEANOS.items()
}

OUTRAS_MATRIZES_DISPONIBILIDADE_BOOLEANOS = (
    (IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(7, time(23, 0), 1, time(0, 0), UTC), [
        [False] * 23 + [True] * 1,
        [False] * 24,
        [False] * 24,
        [False] * 24,
        [False] * 24,
        [False] * 24,
        [False] * 24,
    ]),
    (IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(7, time(23, 0), 1, time(1, 0), UTC), [
        [False] * 23 + [True] * 1,
        [True] * 1 + [False] * 23,
        [False] * 24,
        [False] * 24,
        [False] * 24,
        [False] * 24,
        [False] * 24,
    ]),
    (IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(7, time(22, 0), 2, time(2, 0), UTC), [
        [False] * 22 + [True] * 2,
        [True] * 24,
        [True] * 2 + [False] * 22,
        [False] * 24,
        [False] * 24,
        [False] * 24,
        [False] * 24,
    ]),
    (IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(6, time(22, 0), 2, time(23, 0), UTC), [
        [True] * 24,
        [True] * 24,
        [True] * 23 + [False] * 1,
        [False] * 24,
        [False] * 24,
        [False] * 24,
        [False] * 22 + [True] * 2,
    ]),
    (IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(5, time(22, 0), 2, time(3, 0), UTC), [
        [True] * 24,
        [True] * 24,
        [True] * 3 + [False] * 21,
        [False] * 24,
        [False] * 24,
        [False] * 22 + [True] * 2,
        [True] * 24,
    ]),
    (IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(4, time(22, 0), 3, time(0, 0), UTC), [
        [True] * 24,
        [True] * 24,
        [True] * 24,
        [False] * 24,
        [False] * 22 + [True] * 2,
        [True] * 24,
        [True] * 24,
    ]),
    (IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(6, time(13, 0), 5, time(13, 0), UTC), [
        [True] * 24,
        [True] * 24,
        [True] * 24,
        [True] * 24,
        [True] * 24,
        [True] * 13 + [False] * 11,
        [False] * 13 + [True] * 11,
    ]),
    (IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(4, time(0, 0), 4, time(0, 0), UTC), [
        [True] * 24,
        [True] * 24,
        [True] * 24,
        [True] * 24,
        [True] * 24,
        [True] * 24,
        [True] * 24,
    ]),
    (IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(3, time(10, 0), 3, time(12, 0), UTC), [
        [False] * 24,
        [False] * 24,
        [False] * 24,
        [False] * 10 + [True] * 2 + [False] * 12,
        [False] * 24,
        [False] * 24,
        [False] * 24,
    ]),
    (IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(2, time(12, 0), 2, time(10, 0), UTC), [
        [True] * 24,
        [True] * 24,
        [True] * 10 + [False] * 2 + [True] * 12,
        [True] * 24,
        [True] * 24,
        [True] * 24,
        [True] * 24,
    ]),
)

OUTRAS_MATRIZES_DISPONIBILIDADE_BOOLEANOS_EM_JSON = (
    (intervalo, json.dumps(matriz)) for intervalo, matriz in OUTRAS_MATRIZES_DISPONIBILIDADE_BOOLEANOS
)


class PsicologoModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        Especializacao.objects.create(titulo='Depressão', descricao='Tratamento de depressão e transtornos relacionados.')
        Especializacao.objects.create(titulo='Ansiedade', descricao='Tratamento de transtornos de ansiedade e fobias.')

        cls.especializacoes = [
            Especializacao.objects.create(titulo='Psicologia Clínica', descricao='Tratamento de distúrbios emocionais e comportamentais.'),
            Especializacao.objects.create(titulo='Psicologia Escolar', descricao='Apoio psicológico em ambientes educacionais.'),
            Especializacao.objects.create(titulo='Psicologia Organizacional', descricao='Consultoria e desenvolvimento organizacional.'),
        ]
        cls.paciente = Paciente.objects.create(
            usuario=Usuario.objects.create_user(email="paciente@example.com", password="senha123"),
            cpf="342.738.610-46",
        )
        cls.usuario_com_psicologo = Usuario.objects.create_user(
            email='psicologo@example.com',
            password='senha456',
        )
        cls.psicologo = Psicologo.objects.create(
            usuario=cls.usuario_com_psicologo,
            nome_completo='Wanessa Vasconcelos',
            crp='06/12345',
            sobre_mim='Psicóloga clínica com 10 anos de experiência.',
            valor_consulta=Decimal('100.00'),
        )
        cls.psicologo.especializacoes.set(cls.especializacoes)
        cls.set_disponibilidade_generica(cls.psicologo)

        cls.psicologo_sempre_disponivel = Psicologo.objects.create(
            usuario=Usuario.objects.create_user(email="psicologo.hiperativo@example.com", password="senha123"),
            nome_completo='Psicólogo Hiperativo',
            crp='06/22223',
            sobre_mim='Disponível 24 horas por dia.',
            valor_consulta=Decimal('100.00'),
        )

        cls.psicologo_sempre_disponivel.especializacoes.set(cls.especializacoes)
        IntervaloDisponibilidade.objects.criar_por_dia_semana_e_hora(
            dia_semana_inicio_iso=1,
            hora_inicio=time(0, 0),
            dia_semana_fim_iso=1,
            hora_fim=time(0, 0),
            fuso=UTC,
            psicologo=cls.psicologo_sempre_disponivel,
        ),

    @classmethod
    def set_disponibilidade_generica(cls, psicologo):
        intervalos = [
            (7, time(22, 0), 1, time(2, 0)),
            (1, time(8, 0), 1, time(12, 0)),
            (1, time(14, 0), 1, time(18, 0)),
            (2, time(8, 0), 2, time(12, 0)),
            (2, time(14, 0), 2, time(18, 0)),
            (3, time(8, 0), 3, time(12, 0)),
            (3, time(14, 0), 3, time(18, 0)),
            (4, time(22, 0), 4, time(23, 0)),
            (5, time(1, 0), 5, time(3, 0)),
            (6, time(23, 0), 7, time(12, 0)),
        ]

        for intervalo in intervalos:
            IntervaloDisponibilidade.objects.criar_por_dia_semana_e_hora(
                dia_semana_inicio_iso=intervalo[0],
                hora_inicio=intervalo[1],
                dia_semana_fim_iso=intervalo[2],
                hora_fim=intervalo[3],
                fuso=UTC,
                psicologo=psicologo,
            )
        
    def test_str_representation(self):
        self.assertEqual(str(self.psicologo), 'Wanessa Vasconcelos')

    def test_dados_corretos(self):
        self.assertEqual(self.psicologo.nome_completo, 'Wanessa Vasconcelos')
        self.assertEqual(self.psicologo.crp, '06/12345')
        self.assertEqual(self.psicologo.usuario, self.usuario_com_psicologo)
        self.assertEqual(self.psicologo.sobre_mim, 'Psicóloga clínica com 10 anos de experiência.')
        self.assertEqual(self.psicologo.valor_consulta, Decimal('100.00'))
        self.assertQuerySetEqual(self.psicologo.especializacoes.all(), self.especializacoes, ordered=False)
        self.assertQuerySetEqual(self.psicologo.disponibilidade.all(), IntervaloDisponibilidade.objects.filter(psicologo=self.psicologo), ordered=False)
        self.assertIsNone(self.psicologo.foto.name)

    def test_fk_usuario_obrigatoria(self):
        with self.assertRaisesMessage(IntegrityError, "NOT NULL"):
            Psicologo.objects.create(
                nome_completo='Psicólogo sem usuário',
                crp='06/12345',
            )

    def test_valor_consulta_invalido(self):
        valores_invalidos = [
            Decimal('0.00'),
            Decimal('5000.00'),
            Decimal('-100.00'),
            Decimal('19.99'),
        ]

        for valor in valores_invalidos:
            with self.subTest(valor=valor):
                with self.assertRaises(ValidationError) as ctx:
                    Psicologo(
                        usuario=self.usuario_com_psicologo,
                        nome_completo='Psicólogo Inválido',
                        crp='06/12345',
                        valor_consulta=valor
                    ).full_clean()

                self.assertEqual(
                    'valor_consulta_invalido',
                    ctx.exception.error_dict["valor_consulta"][0].code,
                )

    def test_crp_unico(self):
        usuario = Usuario.objects.create_user(
            email='psicologo2@example.com',
            password='senha123'
        )
        with self.assertRaisesMessage(IntegrityError, "UNIQUE"):
            Psicologo.objects.create(
                usuario=usuario,
                nome_completo='Maria Souza',
                crp='06/12345',
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

        usuario = Usuario.objects.create_user(email="crp.invalido@example.com", password="senha123")

        for crp in crps_invalidos:
            with self.subTest(crp=crp):
                with self.assertRaises(ValidationError) as ctx:
                    Psicologo(
                        usuario=usuario,
                        nome_completo='Psicólogo Inválido',
                        crp=crp,
                    ).full_clean()

                self.assertEqual(
                    'crp_invalido',
                    ctx.exception.error_dict["crp"][0].code,
                )

    def test_impede_usuario_com_paciente(self):
        usuario_com_paciente = Usuario.objects.create_user(
            email='psicologo2@example.com',
            password='senha789'
        )
        Paciente.objects.create(
            usuario=usuario_com_paciente,
            nome='Laura Mendes',
            cpf='555.666.777-88'
        )
        psicologo_em_usuario_com_paciente = Psicologo(
            usuario=usuario_com_paciente,
            nome_completo='Novo Psicólogo',
            crp='06/99999'
        )

        with self.assertRaises(ValidationError) as ctx:
            psicologo_em_usuario_com_paciente.full_clean()

        self.assertEqual(
            "paciente_ja_relacionado",
            ctx.exception.error_dict["usuario"][0].code,
        )

    def test_impede_usuario_com_outro_psicologo(self):
        psicologo_em_usuario_com_psicologo = Psicologo(
            usuario=self.usuario_com_psicologo,
            nome_completo='Outro Psicólogo',
            crp='06/88888',
        )

        with self.assertRaises(ValidationError) as ctx:
            psicologo_em_usuario_com_psicologo.full_clean()

        self.assertEqual(
            'unique',
            ctx.exception.error_dict['usuario'][0].code
        )

    def test_primeiro_nome(self):
        self.assertEqual(self.psicologo.primeiro_nome, 'Wanessa')

    def test_esta_com_perfil_completo(self):
        with self.subTest(psicologo=self.psicologo.__dict__):    
            self.assertTrue(self.psicologo.esta_com_perfil_completo)

        psicologos_com_perfil_incompleto = {
            "falta_especializacao": Psicologo.objects.create(
                usuario=Usuario.objects.create_user(email='usuario1@example.com', password='senha123'),
                nome_completo='Psicólogo Incompleto',
                crp='06/11112',
                valor_consulta=Decimal('100.00'),
            ),
            "falta_disponibilidade": Psicologo.objects.create(
                usuario=Usuario.objects.create_user(email='usuario2@example.com', password='senha123'),
                nome_completo='Psicólogo Incompleto',
                crp='06/11113',
                valor_consulta=Decimal('100.00'),
            ),
            "falta_valor_consulta": Psicologo.objects.create(
                usuario=Usuario.objects.create_user(email='usuario3@example.com', password='senha123'),
                nome_completo='Psicólogo Incompleto',
                crp='06/11114',
            ),
        }

        for motivo, psicologo in psicologos_com_perfil_incompleto.items():
            if motivo != "falta_especializacao":
                psicologo.especializacoes.set(self.especializacoes)
            if motivo != "falta_disponibilidade":
                self.set_disponibilidade_generica(psicologo)

            with self.subTest(motivo=motivo, psicologo=psicologo.__dict__):
                self.assertFalse(psicologo.esta_com_perfil_completo)

    def test_tem_intervalo_em(self):
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
        
        for fuso in FUSOS_PARA_TESTE:
            for expectativa, datas_hora in datas_hora_para_teste.items():
                for data_hora in datas_hora:
                    
                    data_hora = timezone.localtime(data_hora, fuso)

                    with self.subTest(data_hora=data_hora):
                        if expectativa == "tem_intervalo":    
                            self.assertTrue(self.psicologo._tem_intervalo_em(data_hora))
                        elif expectativa == "nao_tem_intervalo":
                            self.assertFalse(self.psicologo._tem_intervalo_em(data_hora))

    def test_get_intervalos_do_mais_proximo_ao_mais_distante_partindo_de(self):
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

        for psicologo in [self.psicologo, self.psicologo_sempre_disponivel]:
            for data_hora in datas_hora_para_teste:
                for fuso in FUSOS_PARA_TESTE:
                    data_hora = timezone.localtime(data_hora, fuso)

                    final_de_consulta_mais_proximo_possivel = converter_dia_semana_iso_com_hora_para_data_hora(
                            data_hora.isoweekday(),
                            data_hora.time(),
                            data_hora.tzinfo,
                        ) + CONSULTA_ANTECEDENCIA_MINIMA + CONSULTA_DURACAO
                
                    intervalos_ordenados = psicologo._get_intervalos_do_mais_proximo_ao_mais_distante_partindo_de(data_hora)

                    intervalos_essa_semana = []
                    intervalos_proxima_semana = []

                    for intervalo in intervalos_ordenados.iterator():
                        if intervalo.proximidade_semana == 0:
                            intervalos_essa_semana.append(intervalo)
                        elif intervalo.proximidade_semana == 1:
                            intervalos_proxima_semana.append(intervalo)

                    with self.subTest(
                        final_de_consulta_mais_proximo_possivel=final_de_consulta_mais_proximo_possivel,
                        intervalos_ordenados=intervalos_ordenados,
                        intervalos_essa_semana=intervalos_essa_semana,
                        intervalos_proxima_semana=intervalos_proxima_semana,
                    ):
                        self.assertQuerySetEqual(intervalos_ordenados, psicologo.disponibilidade.all(), ordered=False)

                        atual = final_de_consulta_mais_proximo_possivel

                        for intervalo in intervalos_essa_semana:
                            data_hora_fim = intervalo.data_hora_fim
                            self.assertGreaterEqual(data_hora_fim, atual)
                            atual = data_hora_fim

                        atual = final_de_consulta_mais_proximo_possivel

                        for intervalo in reversed(intervalos_proxima_semana):
                            data_hora_fim = intervalo.data_hora_fim
                            self.assertLess(data_hora_fim, atual)
                            atual = data_hora_fim

    def test_proxima_data_hora_agendavel(self):
        self.skipTest("TODO test_proxima_data_hora_agendavel")

    def test_get_matriz_disponibilidade_booleanos_em_json(self):
        for fuso, matriz_em_json in MATRIZES_DISPONIBILIDADE_GENERICA_BOOLEANOS_EM_JSON.items():
            with timezone.override(fuso), self.subTest(fuso=fuso, psicologo=self.psicologo.__dict__):
                self.assertEqual(
                    self.psicologo.get_matriz_disponibilidade_booleanos_em_json(),
                    matriz_em_json,
                )
                self.assertEqual(
                    get_matriz_disponibilidade_booleanos_em_json(self.psicologo.disponibilidade),
                    matriz_em_json,
                )

        psicologo_dummy = Psicologo.objects.create(
            usuario=Usuario.objects.create_user(email="psicologo.dummy@example.com", password="dummy123"),
            nome_completo="Psicologo Dummy",
            crp='06/94949',
            sobre_mim='Psicólogo dummy feito apenas para testes.',
        )
        fuso = UTC

        with timezone.override(fuso):
            for intervalo, matriz in OUTRAS_MATRIZES_DISPONIBILIDADE_BOOLEANOS_EM_JSON:
                psicologo_dummy.disponibilidade.all().delete()
                intervalo.psicologo = psicologo_dummy
                intervalo.save()
                
                with self.subTest(fuso=fuso, intervalo=intervalo.__dict__):
                    self.assertEqual(
                        psicologo_dummy.get_matriz_disponibilidade_booleanos_em_json(),
                        matriz,
                    )
                    self.assertEqual(
                        get_matriz_disponibilidade_booleanos_em_json(psicologo_dummy.disponibilidade),
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

        def fazer_assertions_para_cada_fuso(*, metodo_assertion, data_hora, psicologo, msg=""):
            with self.subTest(data_hora=data_hora, psicologo=psicologo.__dict__):
                for fuso in FUSOS_PARA_TESTE:
                    print("localtime: ", timezone.localtime(data_hora, fuso))
                    esta_agendavel_em = psicologo.esta_agendavel_em(timezone.localtime(data_hora, fuso))
                    metodo_assertion(esta_agendavel_em, msg)

        agora = timezone.localtime()
        proxima_data_hora_agendavel = self.psicologo.proxima_data_hora_agendavel

        fazer_assertions_para_cada_fuso(
            metodo_assertion=self.assertFalse,
            data_hora=agora - timedelta(minutes=1),
            psicologo=self.psicologo,
            msg=MotivosParaNaoEstarAgendavel.PASSADO,
        )

        fazer_assertions_para_cada_fuso(
            metodo_assertion=self.assertFalse,
            data_hora=agora + CONSULTA_ANTECEDENCIA_MINIMA - timedelta(minutes=1),
            psicologo=self.psicologo,
            msg=MotivosParaNaoEstarAgendavel.ANTECEDENCIA_MUITO_PEQUENA,
        )

        fazer_assertions_para_cada_fuso(
            metodo_assertion=self.assertFalse,
            data_hora=agora + CONSULTA_ANTECEDENCIA_MAXIMA + timedelta(days=1),
            psicologo=self.psicologo,
            msg=MotivosParaNaoEstarAgendavel.ANTECEDENCIA_MUITO_GRANDE,
        )

        fazer_assertions_para_cada_fuso(
            metodo_assertion=self.assertFalse,
            data_hora=proxima_data_hora_agendavel + CONSULTA_ANTECEDENCIA_MAXIMA,
            psicologo=self.psicologo,
            msg=MotivosParaNaoEstarAgendavel.ANTECEDENCIA_MUITO_GRANDE,
        )

        fazer_assertions_para_cada_fuso(
            metodo_assertion=self.assertFalse,
            data_hora=proxima_data_hora_agendavel - CONSULTA_DURACAO,
            psicologo=self.psicologo,
            msg=MotivosParaNaoEstarAgendavel.ANTES_DA_PROXIMA_DATA_HORA_AGENDAVEL,
        )

        intervalos_do_psicologo = self.psicologo.disponibilidade.all()
        intervalo = intervalos_do_psicologo.first()
        fuso_intervalo = intervalo.data_hora_inicio.tzinfo
        data_intervalo = intervalo.data_hora_inicio.date()
        agora_fuso_intervalo = timezone.localtime(agora, fuso_intervalo)
        diferenca_dias_semana = data_intervalo.isoweekday() - agora_fuso_intervalo.isoweekday()
        diferenca_dias_semana = diferenca_dias_semana + 7 if diferenca_dias_semana < 0 else diferenca_dias_semana

        data_hora_inicio = datetime.combine(
            agora_fuso_intervalo.date(),
            intervalo.data_hora_inicio.time(),
            fuso_intervalo,
        ) + timedelta(days=diferenca_dias_semana)

        fazer_assertions_para_cada_fuso(
            metodo_assertion=self.assertTrue,
            data_hora=data_hora_inicio,
            psicologo=self.psicologo,
        )

        intervalo.delete()

        fazer_assertions_para_cada_fuso(
            metodo_assertion=self.assertFalse,
            data_hora=data_hora_inicio,
            psicologo=self.psicologo,
            msg=MotivosParaNaoEstarAgendavel.NAO_HA_INTERVALO,
        )

        intervalos_do_psicologo.delete()
        
        fazer_assertions_para_cada_fuso(
            metodo_assertion=self.assertFalse,
            data_hora=proxima_data_hora_agendavel,
            psicologo=self.psicologo,
            msg=MotivosParaNaoEstarAgendavel.NAO_HA_INTERVALO,
        )

        self.set_disponibilidade_generica(self.psicologo)

        fazer_assertions_para_cada_fuso(
            metodo_assertion=self.assertTrue,
            data_hora=proxima_data_hora_agendavel,
            psicologo=self.psicologo,
        )

        consulta = Consulta.objects.create(
            data_hora_agendada=proxima_data_hora_agendavel,
            paciente=self.paciente,
            psicologo=self.psicologo,
        )

        fazer_assertions_para_cada_fuso(
            metodo_assertion=self.assertFalse,
            data_hora=proxima_data_hora_agendavel,
            psicologo=self.psicologo,
            msg=MotivosParaNaoEstarAgendavel.JA_HA_CONSULTA,
        )

        fazer_assertions_para_cada_fuso(
            metodo_assertion=self.assertFalse,
            data_hora=proxima_data_hora_agendavel + CONSULTA_DURACAO - timedelta(minutes=1),
            psicologo=self.psicologo,
            msg=MotivosParaNaoEstarAgendavel.JA_HA_CONSULTA,
        )

        fazer_assertions_para_cada_fuso(
            metodo_assertion=self.assertFalse,
            data_hora=proxima_data_hora_agendavel + timedelta(minutes=1),
            psicologo=self.psicologo,
            msg=MotivosParaNaoEstarAgendavel.JA_HA_CONSULTA,
        )
        
        consulta.estado = EstadoConsulta.CANCELADA
        consulta.save()

        fazer_assertions_para_cada_fuso(
            metodo_assertion=self.assertTrue,
            data_hora=proxima_data_hora_agendavel,
            psicologo=self.psicologo,
        )

        fazer_assertions_para_cada_fuso(
            metodo_assertion=self.assertFalse,
            data_hora=agora - timedelta(minutes=1),
            psicologo=self.psicologo_sempre_disponivel,
            msg=MotivosParaNaoEstarAgendavel.PASSADO,
        )

        fazer_assertions_para_cada_fuso(
            metodo_assertion=self.assertFalse,
            data_hora=agora,
            psicologo=self.psicologo_sempre_disponivel,
            msg=MotivosParaNaoEstarAgendavel.ANTECEDENCIA_MUITO_PEQUENA,
        )

        fazer_assertions_para_cada_fuso(
            metodo_assertion=self.assertFalse,
            data_hora=agora + timedelta(minutes=1),
            psicologo=self.psicologo_sempre_disponivel,
            msg=MotivosParaNaoEstarAgendavel.ANTECEDENCIA_MUITO_PEQUENA,
        )

        fazer_assertions_para_cada_fuso(
            metodo_assertion=self.assertFalse,
            data_hora=agora + CONSULTA_ANTECEDENCIA_MAXIMA + timedelta(days=1),
            psicologo=self.psicologo_sempre_disponivel,
            msg=MotivosParaNaoEstarAgendavel.ANTECEDENCIA_MUITO_GRANDE,
        )

        fazer_assertions_para_cada_fuso(
            metodo_assertion=self.assertTrue,
            data_hora=agora + CONSULTA_ANTECEDENCIA_MINIMA + timedelta(minutes=1),
            psicologo=self.psicologo_sempre_disponivel,
        )

        fazer_assertions_para_cada_fuso(
            metodo_assertion=self.assertTrue,
            data_hora=agora + CONSULTA_ANTECEDENCIA_MAXIMA - timedelta(minutes=1),
            psicologo=self.psicologo_sempre_disponivel,
        )

        proxima_data_hora_agendavel = self.psicologo_sempre_disponivel.proxima_data_hora_agendavel

        fazer_assertions_para_cada_fuso(
            metodo_assertion=self.assertTrue,
            data_hora=proxima_data_hora_agendavel,
            psicologo=self.psicologo_sempre_disponivel,
        )
