from django.db import IntegrityError
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from terapia.models import Paciente, Psicologo, Especializacao
from decimal import Decimal


Usuario = get_user_model()


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
        cls.usuario_psicologo = Usuario.objects.create_user(
            email='psicologo@example.com',
            password='senha456'
        )
        cls.psicologo = Psicologo.objects.create(
            usuario=cls.usuario_psicologo,
            nome_completo='Wanessa Vasconcelos',
            crp='06/12345',
            sobre_mim='Psicóloga clínica com 10 anos de experiência.',
            valor_consulta=Decimal('100.00'),
        )
        cls.psicologo.especializacoes.set(cls.especializacoes)

    def test_str_representation(self):
        self.assertEqual(str(self.psicologo), 'Wanessa Vasconcelos')

    def test_criar_psicologo(self):
        """
        Inserir dados válidos.
        """
        self.assertEqual(self.psicologo.nome_completo, 'Wanessa Vasconcelos')
        self.assertEqual(self.psicologo.crp, '06/12345')
        self.assertEqual(self.psicologo.usuario, self.usuario_psicologo)
        self.assertEqual(self.psicologo.sobre_mim, 'Psicóloga clínica com 10 anos de experiência.')
        self.assertEqual(self.psicologo.valor_consulta, Decimal('100.00'))
        self.assertQuerySetEqual(self.psicologo.especializacoes.all(), self.especializacoes, ordered=False)
        self.assertIsNone(self.psicologo.foto.name)

    def test_valor_consulta_invalido(self):
        pass

    def test_crp_unico(self):
        """
        Garantir unicidade de CPF.
        """
        usuario2 = Usuario.objects.create_user(
            email='paciente2@example.com',
            password='senha123'
        )
        with self.assertRaises(IntegrityError) as ctx:
            Psicologo.objects.create(
                usuario=usuario2,
                nome_completo='Maria Souza',
                crp='06/12345',
            )
        self.assertIn('unique constraint failed', str(ctx.exception).lower())

    def test_crp_invalido(self):
        """
        Inserir um CRP inexistente.
        """
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
        """
        Impedir usuário já vinculado a um paciente.
        """
        usuario_paciente = Usuario.objects.create_user(
            email='paciente2@example.com',
            password='senha789'
        )
        Paciente.objects.create(
            usuario=usuario_paciente,
            nome='Laura Mendes',
            cpf='555.666.777-88'
        )
        psicologo_em_usuario_paciente = Psicologo(
            usuario=usuario_paciente,
            nome_completo='Novo Psicólogo',
            crp='06/99999'
        )

        with self.assertRaises(ValidationError) as ctx:
            psicologo_em_usuario_paciente.full_clean()

        self.assertEqual(
            "paciente_ja_relacionado",
            ctx.exception.error_dict["usuario"][0].code,
        )

    def test_impede_usuario_com_outro_psicologo(self):
        """
        Impedir usuário já vinculado a outro psicólogo.
        """
        psicologo_em_usuario_psicologo = Psicologo(
            usuario=self.usuario_psicologo,
            nome_completo='Outro Psicólogo',
            crp='06/88888',
        )

        with self.assertRaises(ValidationError) as ctx:
            psicologo_em_usuario_psicologo.full_clean()

        self.assertEqual(
            'unique',
            ctx.exception.error_dict['usuario'][0].code
        )
