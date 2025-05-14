from django.test import TestCase
from django.contrib.auth import get_user_model
from terapia.models import Paciente

User = get_user_model()


class PacienteModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario_paciente = User.objects.create_user(
            email='paciente@example.com',
            password='senha123'
        )

    def test_cpf_unico(self):
        """
        TU01-B: Garantir unicidade de CPF.
        """
        Paciente.objects.create(
            usuario=self.usuario_paciente,
            nome='João da Silva',
            cpf='123.456.789-00'
        )
        usuario2 = User.objects.create_user(
            email='paciente2@example.com',
            password='senha123'
        )
        with self.assertRaises(Exception) as ctx:
            Paciente.objects.create(
                usuario=usuario2,
                nome='Maria Souza',
                cpf='123.456.789-00'
            )
        self.assertIn('unique constraint failed', str(ctx.exception).lower())
