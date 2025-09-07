from django.core.exceptions import ValidationError
from django.test import TestCase
from django.contrib.auth import get_user_model
from terapia.models import Paciente, Psicologo
from django.db import IntegrityError


Usuario = get_user_model()


class PacienteModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario_com_paciente = Usuario.objects.create_user(
            email='paciente@example.com',
            password='senha123'
        )

        cls.paciente = Paciente.objects.create(
            usuario=cls.usuario_com_paciente,
            nome='Carlos Alberto',
            cpf='987.654.321-11',
        )

    def test_str_representation(self):
        self.assertEqual(str(self.paciente), 'Carlos Alberto')

    def test_dados_corretos(self):
        self.assertEqual(self.paciente.nome, 'Carlos Alberto')
        self.assertEqual(self.paciente.cpf, '987.654.321-11')
        self.assertEqual(self.paciente.usuario, self.usuario_com_paciente)
        self.assertIsNone(self.paciente.foto.name)

    def test_fk_usuario_obrigatoria(self):
        with self.assertRaisesMessage(IntegrityError, "NOT NULL"):
            Paciente.objects.create(
                nome='Paciente sem usuário',
                cpf='369.720.320-75',
            )

    def test_cpf_unico(self):
        usuario2 = Usuario.objects.create_user(
            email='paciente2@example.com',
            password='senha123'
        )
        with self.assertRaisesMessage(IntegrityError, "UNIQUE"):
            Paciente.objects.create(
                usuario=usuario2,
                nome='Maria Souza',
                cpf='987.654.321-11',
            )

    def test_cpf_invalido(self):
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
        usuario_com_psicologo = Usuario.objects.create_user(
            email='psicologo@example.com',
            password='senha456',
        )
        Psicologo.objects.create(
            usuario=usuario_com_psicologo,
            nome_completo='Dra. Ana Paula',
            crp='06/12345',
        )
        paciente_em_usuario_com_psicologo = Paciente(
            usuario=usuario_com_psicologo,
            nome='Novo Paciente',
            cpf='446.753.260-99',
        )

        with self.assertRaises(ValidationError) as ctx:
            paciente_em_usuario_com_psicologo.full_clean()

        self.assertEqual(
            "psicologo_ja_relacionado",
            ctx.exception.error_dict["usuario"][0].code,
        )

    def test_impede_usuario_com_outro_paciente(self):
        paciente_em_usuario_com_paciente = Paciente(
            usuario=self.usuario_com_paciente,
            nome='Outro Paciente',
            cpf='963.562.490-56',
        )

        with self.assertRaises(ValidationError) as ctx:
            paciente_em_usuario_com_paciente.full_clean()

        self.assertEqual(
            'unique',
            ctx.exception.error_dict['usuario'][0].code
        )
