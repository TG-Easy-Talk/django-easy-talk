from django.test import TestCase
from django.utils import timezone
from datetime import date, time, timedelta, datetime, UTC
from zoneinfo import ZoneInfo
from terapia.models import Psicologo, IntervaloDisponibilidadeTemplate, SemanaDisponibilidadeConfig, IntervaloDisponibilidadeOverride
from terapia.services import DisponibilidadeService
from terapia.tests.model_test_case import ModelTestCase
from django.contrib.auth import get_user_model

Usuario = get_user_model()

class DisponibilidadeServiceTest(ModelTestCase):
    def setUp(self):
        super().setUp()
        user = Usuario.objects.create_user(email=f'test_psi_{timezone.now().timestamp()}@example.com', password='password')
        self.psicologo = Psicologo.objects.create(
            usuario=user,
            nome_completo='Test Psychologist',
            crp='12/34567'
        )

    def test_obter_semana_inicio(self):
        # 2024-07-01 is a Monday
        d = date(2024, 7, 1)
        self.assertEqual(DisponibilidadeService.obter_semana_inicio(d), d)
        
        # 2024-07-03 is a Wednesday
        d2 = date(2024, 7, 3)
        self.assertEqual(DisponibilidadeService.obter_semana_inicio(d2), d)
        
        # 2024-07-07 is a Sunday
        d3 = date(2024, 7, 7)
        self.assertEqual(DisponibilidadeService.obter_semana_inicio(d3), d)

    def test_salvar_template_de_matriz(self):
        # Create a matrix with one slot: Monday 08:00-09:00
        # Matrix is 7x24 (1 hour slots)
        # 08:00 is slot 8
        # 09:00 is slot 9
        matriz = [[False] * 24 for _ in range(7)]
        matriz[1][8] = True # Mon 08:00-09:00 (single slot)
        
        DisponibilidadeService.salvar_template_de_matriz(self.psicologo, matriz)
        
        templates = IntervaloDisponibilidadeTemplate.objects.filter(psicologo=self.psicologo)
        self.assertEqual(templates.count(), 1)
        t = templates.first()
        self.assertEqual(t.dia_semana_inicio_iso, 1)
        self.assertEqual(t.hora_inicio, time(8, 0))
        self.assertEqual(t.dia_semana_fim_iso, 1)
        self.assertEqual(t.hora_fim, time(9, 0))

    def test_replicar_template_para_semanas(self):
        semana_inicio = date(2024, 7, 1)
        DisponibilidadeService.replicar_template_para_semanas(self.psicologo, semana_inicio, 3)
        
        configs = SemanaDisponibilidadeConfig.objects.filter(psicologo=self.psicologo)
        self.assertEqual(configs.count(), 3)
        
        expected_weeks = [date(2024, 7, 8), date(2024, 7, 15), date(2024, 7, 22)]
        for config in configs:
            self.assertIn(config.semana_inicio, expected_weeks)
            self.assertEqual(config.comportamento, 'TEMPLATE')

    def test_obter_intervalos_para_semana_template(self):
        # Setup template: Mon 10:00-11:00
        IntervaloDisponibilidadeTemplate.objects.create(
            psicologo=self.psicologo,
            dia_semana_inicio_iso=1,
            hora_inicio=time(10, 0),
            dia_semana_fim_iso=1,
            hora_fim=time(11, 0)
        )
        
        semana = date(2024, 7, 1) # Monday
        intervalos = DisponibilidadeService.obter_intervalos_para_semana(self.psicologo, semana)
        
        self.assertEqual(len(intervalos), 1)
        self.assertIsInstance(intervalos[0], dict)
        # Check if dates are correct for that week
        # 2024-07-01 10:00
        # With UTC fix, it should be 10:00 UTC
        expected_start = datetime(2024, 7, 1, 10, 0, tzinfo=UTC)
        self.assertEqual(intervalos[0]['data_hora_inicio'], expected_start)

    def test_obter_intervalos_para_semana_override(self):
        semana = date(2024, 7, 1)
        
        # Create override config
        SemanaDisponibilidadeConfig.objects.create(
            psicologo=self.psicologo,
            semana_inicio=semana,
            comportamento='CUSTOM'
        )
        
        # Create override interval
        start = timezone.make_aware(timezone.datetime(2024, 7, 2, 14, 0)) # Tuesday
        end = timezone.make_aware(timezone.datetime(2024, 7, 2, 15, 0))
        
        IntervaloDisponibilidadeOverride.objects.create(
            psicologo=self.psicologo,
            semana_inicio=semana,
            data_hora_inicio=start,
            data_hora_fim=end
        )
        
        intervalos = DisponibilidadeService.obter_intervalos_para_semana(self.psicologo, semana)
        self.assertEqual(len(intervalos), 1)
        self.assertIsInstance(intervalos[0], IntervaloDisponibilidadeOverride)
        self.assertEqual(intervalos[0].data_hora_inicio, start)

    def test_obter_intervalos_para_semana_unavailable(self):
        semana = date(2024, 7, 1)
        SemanaDisponibilidadeConfig.objects.create(
            psicologo=self.psicologo,
            semana_inicio=semana,
            comportamento='UNAVAILABLE'
        )
        
        intervalos = DisponibilidadeService.obter_intervalos_para_semana(self.psicologo, semana)
        self.assertEqual(len(intervalos), 0)

    def test_repro_timezone_issue(self):
        # Setup template: Mon 00:00-02:00 UTC
        IntervaloDisponibilidadeTemplate.objects.create(
            psicologo=self.psicologo,
            dia_semana_inicio_iso=1,
            hora_inicio=time(0, 0),
            dia_semana_fim_iso=1,
            hora_fim=time(2, 0)
        )
        
        # Override timezone to UTC-5
        tz = ZoneInfo("Etc/GMT+5")
        
        with timezone.override(tz):
            # Week of 2024-07-08 (Monday)
            semana = date(2024, 7, 8)
            
            intervalos = DisponibilidadeService.obter_intervalos_para_semana(self.psicologo, semana)
            
            self.assertEqual(len(intervalos), 1)
            start = intervalos[0]['data_hora_inicio']
            
            # Expect 00:00 UTC
            self.assertEqual(start.astimezone(UTC), datetime(2024, 7, 8, 0, 0, tzinfo=UTC))
