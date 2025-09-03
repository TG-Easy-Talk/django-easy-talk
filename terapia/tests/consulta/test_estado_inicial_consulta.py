import datetime
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from terapia.models import Paciente, Psicologo, Consulta, EstadoConsulta

Usuario = get_user_model()


class ConsultaModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario_cliente = Usuario.objects.create_user(
            email='c1@example.com',
            password='senha123'
        )
        cls.usuario_psicologo = Usuario.objects.create_user(
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
        cls.base_dt = timezone.make_aware(datetime.datetime(2025, 12, 26, 13, 30))
        start = cls.base_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        cls.psicologo.disponibilidade.create(
            data_hora_inicio=start,
            data_hora_fim=end,
        )

    def test_tu03_d_estado_solicitada(self):
        """
        TU03-D: Estado padrão de SOLICITADA.
        """
        consulta = Consulta(
            paciente=self.paciente,
            psicologo=self.psicologo,
            data_hora_agendada=self.base_dt,
            duracao=60,
        )
        self.assertEqual(consulta.estado, EstadoConsulta.SOLICITADA)
