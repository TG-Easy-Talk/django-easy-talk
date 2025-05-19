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

    def test_criar_paciente(self):
        """
        TU01-A: Inserir dados válidos.
        """
        paciente = Paciente.objects.create(
            usuario=self.usuario_paciente,
            nome='João da Silva',
            cpf='123.456.789-00'
        )
        self.assertEqual(paciente.nome, 'João da Silva')
        self.assertEqual(paciente.cpf, '123.456.789-00')
        self.assertEqual(paciente.usuario, self.usuario_paciente)
        self.assertIsNone(paciente.foto.name)
