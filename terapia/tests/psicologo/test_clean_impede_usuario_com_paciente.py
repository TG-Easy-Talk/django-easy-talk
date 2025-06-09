from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from terapia.models import Paciente, Psicologo

User = get_user_model()


class PsicologoModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario_psicologo = User.objects.create_user(
            email='psicologo@example.com',
            password='senha456'
        )

    def test_clean_impede_usuario_com_paciente(self):
        """
        Impedir usuário já vinculado a Paciente.
        """
        usuario_paciente = User.objects.create_user(
            email='paciente2@example.com',
            password='senha789'
        )
        Paciente.objects.create(
            usuario=usuario_paciente,
            nome='Laura Mendes',
            cpf='555.666.777-88'
        )
        psicologo = Psicologo(
            usuario=usuario_paciente,
            nome_completo='Novo Psicólogo',
            crp='06/99999'
        )
        with self.assertRaises(ValidationError) as ctx:
            psicologo.full_clean()

        self.assertEqual(
            "paciente_ja_relacionado",
            ctx.exception.error_dict["usuario"][0].code,
        )
