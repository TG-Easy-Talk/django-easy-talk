from django.core.exceptions import ValidationError
from django.test import TestCase
from django.contrib.auth import get_user_model
from terapia.models import Paciente, Psicologo
from django.db import IntegrityError


Usuario = get_user_model()


class PacienteModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario_paciente = Usuario.objects.create_user(
            email='paciente@example.com',
            password='senha123'
        )

        cls.paciente = Paciente.objects.create(
            usuario=cls.usuario_paciente,
            nome='Carlos Alberto',
            cpf='987.654.321-11',
        )

    def test_str_representation(self):
        self.assertEqual(str(self.paciente), 'Carlos Alberto')

    def test_criar_paciente(self):
        """
        Inserir dados válidos.
        """
        self.assertEqual(self.paciente.nome, 'Carlos Alberto')
        self.assertEqual(self.paciente.cpf, '987.654.321-11')
        self.assertEqual(self.paciente.usuario, self.usuario_paciente)
        self.assertIsNone(self.paciente.foto.name)

    def test_cpf_unico(self):
        """
        Garantir unicidade de CPF.
        """
        usuario2 = Usuario.objects.create_user(
            email='paciente2@example.com',
            password='senha123'
        )
        with self.assertRaises(IntegrityError) as ctx:
            Paciente.objects.create(
                usuario=usuario2,
                nome='Maria Souza',
                cpf='987.654.321-11',
            )
        self.assertIn('unique constraint failed', str(ctx.exception).lower())

    def test_cpf_invalido(self):
        """
        Inserir um CPF inexistente.
        """
        cpfs_invalidos = [
            '574.768.960-67',
            '57476896067',
            '111.111.111-11',
        ]

        usuario = Usuario.objects.create_user(email=f"cpf.invalido@exemplo.com", password="senha123")

        for cpf in cpfs_invalidos:
            with self.subTest(cpf=cpf):
                with self.assertRaises(ValidationError) as ctx:
                    Paciente(
                        usuario=usuario,
                        nome='Paciente Inválido',
                        cpf=cpf,
                    ).full_clean()

                self.assertEqual(
                    'cpf_invalido',
                    ctx.exception.error_dict["cpf"][0].code,
                )

    def test_impede_usuario_com_psicologo(self):
        """
        Impedir usuário já vinculado a um psicólogo.
        """
        usuario_psicologo = Usuario.objects.create_user(
            email='psicologo@example.com',
            password='senha456',
        )
        Psicologo.objects.create(
            usuario=usuario_psicologo,
            nome_completo='Dra. Ana Paula',
            crp='06/12345',
        )
        paciente_em_usuario_psicologo = Paciente(
            usuario=usuario_psicologo,
            nome='Novo Paciente',
            cpf='446.753.260-99',
        )

        with self.assertRaises(ValidationError) as ctx:
            paciente_em_usuario_psicologo.full_clean()

        self.assertEqual(
            "psicologo_ja_relacionado",
            ctx.exception.error_dict["usuario"][0].code,
        )

    def test_impede_usuario_com_outro_paciente(self):
        """
        Impedir usuário já vinculado a outro paciente.
        """
        paciente_em_usuario_paciente = Paciente(
            usuario=self.usuario_paciente,
            nome='Outro Paciente',
            cpf='963.562.490-56',
        )

        with self.assertRaises(ValidationError) as ctx:
            paciente_em_usuario_paciente.full_clean()

        self.assertEqual(
            'unique',
            ctx.exception.error_dict['usuario'][0].code
        )
