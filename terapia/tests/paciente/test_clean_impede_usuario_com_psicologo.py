from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from terapia.models import Paciente, Psicologo

User = get_user_model()


class PacienteModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario_paciente = User.objects.create_user(
            email='paciente@example.com',
            password='senha123'
        )

    def test_clean_impede_usuario_com_psicologo(self):
        """
        TU01-C: Impedir usuário já vinculado a Psicólogo.
        """
        usuario_psicologo = User.objects.create_user(
            email='psicologo@example.com',
            password='senha456'
        )
        Psicologo.objects.create(
            usuario=usuario_psicologo,
            nome_completo='Dra. Ana Paula',
            crp='06/12345'
        )
        paciente = Paciente(
            usuario=usuario_psicologo,
            nome='Novo Paciente',
            cpf='111.222.333-44'
        )
        with self.assertRaises(ValidationError) as ctx:
            paciente.clean()
        self.assertEqual(
            str(ctx.exception),
            "['Este usuário já está relacionado a um psicólogo.']"
        )
