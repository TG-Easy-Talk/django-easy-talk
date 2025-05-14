from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from terapia.models import Paciente

User = get_user_model()


class PacienteModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario_paciente = User.objects.create_user(
            email='paciente@example.com',
            password='senha123'
        )

    def test_cpf_invalido(self):
        """
        TU01-B: Inserir um CPF inexistente.
        """
        paciente = Paciente(
            usuario=self.usuario_paciente,
            nome='Teste Inválido',
            cpf='123'
        )
        with self.assertRaises(ValidationError) as ctx:
            paciente.full_clean()
        self.assertIn(
            'Este CPF é inválido',
            ctx.exception.message_dict.get('cpf', [])
        )
