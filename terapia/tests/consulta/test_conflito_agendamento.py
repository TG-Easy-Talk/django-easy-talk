import datetime
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth import get_user_model
from terapia.models import Paciente, Psicologo, Consulta

User = get_user_model()


class ConsultaModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario_cliente = User.objects.create_user(
            email='c1@example.com',
            password='senha123'
        )
        cls.usuario_psicologo = User.objects.create_user(
            email='p1@example.com',
            password='senha123'
        )
        cls.paciente = Paciente.objects.create(
            usuario=cls.usuario_cliente,
            nome='Cliente Teste',
            cpf='12345678901'
        )
        cls.psicologo = Psicologo.objects.create(
            usuario=cls.usuario_psicologo,
            nome_completo='Psicólogo Teste',
            crp='06/54321'
        )
        cls.base_dt = datetime.datetime(
            2025, 12, 26, 13, 30,
            tzinfo=timezone.get_current_timezone()
        )
        dia = cls.base_dt.isoweekday()
        cls.psicologo.disponibilidade = [{
            "dia_semana": dia,
            "intervalos": [{"horario_inicio": "00:00", "horario_fim": "23:59"}]
        }]
        cls.psicologo.save()

    def test_tu03_e_conflito_agendamento(self):
        """
        TU03-E: Conflito de agendamento no mesmo horário.
        """
        Consulta.objects.create(
            paciente=self.paciente,
            psicologo=self.psicologo,
            data_hora_marcada=self.base_dt,
            duracao=60
        )
        dup = Consulta(
            paciente=self.paciente,
            psicologo=self.psicologo,
            data_hora_marcada=self.base_dt,
            duracao=60
        )
        with self.assertRaises(ValidationError) as cm:
            dup.full_clean()
        self.assertIn(
            "O psicólogo não tem disponibilidade",
            str(cm.exception)
        )
