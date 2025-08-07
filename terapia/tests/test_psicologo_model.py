from django.db import IntegrityError
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from terapia.models import Paciente, Psicologo, Especializacao, IntervaloDisponibilidade
from decimal import Decimal
from datetime import UTC, datetime
from django.utils import timezone


Usuario = get_user_model()

MATRIZ_DISPONIBILIDADE_GENERICA_BOOLEANOS = [
    [False] * 24,
    [False] * 8 + [True] * 4 + [False] * 2 + [True] * 4 + [False] * 6,
    [False] * 8 + [True] * 4 + [False] * 2 + [True] * 4 + [False] * 6,
    [False] * 8 + [True] * 4 + [False] * 2 + [True] * 4 + [False] * 6,
    [False] * 8 + [True] * 4 + [False] * 2 + [True] * 4 + [False] * 6,
    [False] * 24,
    [False] * 24,
]
MATRIZ_DISPONIBILIDADE_GENERICA_BOOLEANOS_EM_JAVASCRIPT = str(MATRIZ_DISPONIBILIDADE_GENERICA_BOOLEANOS).lower()

timezone.activate(UTC)


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
        cls.disponibilidade_generica = [
            IntervaloDisponibilidade(data_hora_inicio=datetime(2024, 7, 1, 8, 0, tzinfo=UTC), data_hora_fim=datetime(2024, 7, 1, 12, 0, tzinfo=UTC)),
            IntervaloDisponibilidade(data_hora_inicio=datetime(2024, 7, 1, 14, 0, tzinfo=UTC), data_hora_fim=datetime(2024, 7, 1, 18, 0, tzinfo=UTC)),
            IntervaloDisponibilidade(data_hora_inicio=datetime(2024, 7, 2, 8, 0, tzinfo=UTC), data_hora_fim=datetime(2024, 7, 2, 12, 0, tzinfo=UTC)),
            IntervaloDisponibilidade(data_hora_inicio=datetime(2024, 7, 2, 14, 0, tzinfo=UTC), data_hora_fim=datetime(2024, 7, 2, 18, 0, tzinfo=UTC)),
            IntervaloDisponibilidade(data_hora_inicio=datetime(2024, 7, 3, 8, 0, tzinfo=UTC), data_hora_fim=datetime(2024, 7, 3, 12, 0, tzinfo=UTC)),
            IntervaloDisponibilidade(data_hora_inicio=datetime(2024, 7, 3, 14, 0, tzinfo=UTC), data_hora_fim=datetime(2024, 7, 3, 18, 0, tzinfo=UTC)),
            IntervaloDisponibilidade(data_hora_inicio=datetime(2024, 7, 4, 8, 0, tzinfo=UTC), data_hora_fim=datetime(2024, 7, 4, 12, 0, tzinfo=UTC)),
            IntervaloDisponibilidade(data_hora_inicio=datetime(2024, 7, 4, 14, 0, tzinfo=UTC), data_hora_fim=datetime(2024, 7, 4, 18, 0, tzinfo=UTC)),
        ]
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

    @classmethod
    def set_disponibilidade_generica(cls, psicologo):
        for intervalo in cls.disponibilidade_generica:
            intervalo.psicologo = psicologo
            intervalo.save()
        
    def test_str_representation(self):
        self.assertEqual(str(self.psicologo), 'Wanessa Vasconcelos')

    def test_dados_corretos(self):
        self.assertEqual(self.psicologo.nome_completo, 'Wanessa Vasconcelos')
        self.assertEqual(self.psicologo.crp, '06/12345')
        self.assertEqual(self.psicologo.usuario, self.usuario_com_psicologo)
        self.assertEqual(self.psicologo.sobre_mim, 'Psicóloga clínica com 10 anos de experiência.')
        self.assertEqual(self.psicologo.valor_consulta, Decimal('100.00'))
        self.assertQuerySetEqual(self.psicologo.especializacoes.all(), self.especializacoes, ordered=False)
        self.assertQuerySetEqual(self.psicologo.disponibilidade.all(), self.disponibilidade_generica, ordered=False)
        self.assertIsNone(self.psicologo.foto.name)

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
        with self.assertRaises(IntegrityError) as ctx:
            Psicologo.objects.create(
                usuario=usuario,
                nome_completo='Maria Souza',
                crp='06/12345',
            )
        self.assertIn('unique constraint failed', str(ctx.exception).lower())

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
        with self.subTest(psicologo=self.psicologo):    
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

            with self.subTest(psicologo=psicologo):
                self.assertFalse(psicologo.esta_com_perfil_completo)

    def test_get_matriz_disponibilidade_booleanos_em_javascript(self):
        self.assertEqual(
            self.psicologo.get_matriz_disponibilidade_booleanos_em_javascript(),
            MATRIZ_DISPONIBILIDADE_GENERICA_BOOLEANOS_EM_JAVASCRIPT,
        )