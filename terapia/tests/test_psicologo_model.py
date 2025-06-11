from django.db import IntegrityError
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from terapia.models import Paciente, Psicologo


Usuario = get_user_model()


class PsicologoModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario_psicologo = Usuario.objects.create_user(
            email='psicologo@example.com',
            password='senha456'
        )
        cls.psicologo = Psicologo.objects.create(
            usuario=cls.usuario_psicologo,
            nome_completo='Wanessa Vasconcelos',
            crp='06/12345',
        )

    def test_str_representation(self):
        self.assertEqual(str(self.psicologo), 'Wanessa Vasconcelos')

    def test_criar_psicologo(self):
        """
        Inserir dados válidos.
        """
        self.assertEqual(self.psicologo.nome_completo, 'Wanessa Vasconcelos')
        self.assertEqual(self.psicologo.crp, '06/12345')
        self.assertEqual(self.psicologo.usuario, self.usuario_psicologo)
        self.assertIsNone(self.psicologo.foto.name)

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
        psicologo_crp_invalido = Psicologo(
            usuario=self.usuario_psicologo,
            nome_completo='Teste Inválido',
            crp='06-12345', # CRP inválido
        )

        with self.assertRaises(ValidationError) as ctx:
            psicologo_crp_invalido.full_clean()

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
