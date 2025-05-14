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

    def test_str_representation(self):
        paciente = Paciente.objects.create(
            usuario=self.usuario_paciente,
            nome='Carlos Alberto',
            cpf='987.654.321-11'
        )
        self.assertEqual(str(paciente), 'Carlos Alberto')
