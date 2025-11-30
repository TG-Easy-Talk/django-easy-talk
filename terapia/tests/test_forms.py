from datetime import datetime, UTC
from django.test import TestCase
from terapia.forms import (
    PsicologoDisponibilidadeChangeForm,
    ConsultaCreationForm,
    PsicologoFiltrosForm,
    ConsultaFiltrosForm,
)
from terapia.models import IntervaloDisponibilidade, Consulta, IntervaloDisponibilidadeOverride
from .model_test_case import ModelTestCase
from django.utils import timezone

class FormsTestCase(ModelTestCase):
    def test_psicologo_disponibilidade_change_form_valid(self):
        """Testa se o formulário de disponibilidade salva corretamente os intervalos."""
        # Matriz de disponibilidade simulando a entrada do frontend (JSON)
        # Segunda-feira (1) das 08:00 às 12:00
        disponibilidade_json = [
            [False] * 48 for _ in range(7)
        ]
        # Índices para 08:00 (8) até 12:00 (12) - cada índice é 60 min
        for i in range(8, 12):
            disponibilidade_json[1][i] = True

        form_data = {
            "disponibilidade": disponibilidade_json
        }
        
        form = PsicologoDisponibilidadeChangeForm(
            data=form_data, 
            instance=self.psicologo_dummy
        )
        
        self.assertTrue(form.is_valid())
        psicologo = form.save()
        
        overrides = IntervaloDisponibilidadeOverride.objects.filter(psicologo=psicologo)
        self.assertTrue(overrides.exists())
        
        # Deve ter criado um intervalo na segunda-feira
        override = overrides.first()
        inicio_local = timezone.localtime(override.data_hora_inicio)
        fim_local = timezone.localtime(override.data_hora_fim)
        
        self.assertEqual(inicio_local.isoweekday(), 1)
        self.assertEqual(inicio_local.hour, 8)
        self.assertEqual(fim_local.hour, 12)

    def test_consulta_creation_form_valid(self):
        """Testa se o formulário de criação de consulta associa corretamente paciente e psicólogo."""
        data_hora = self.psicologo_completo.proxima_data_hora_agendavel
        
        form_data = {
            "data_hora_agendada": data_hora
        }
        
        form = ConsultaCreationForm(
            data=form_data,
            usuario=self.paciente_dummy.usuario,
            psicologo=self.psicologo_completo
        )
        
        self.assertTrue(form.is_valid())
        consulta = form.save()
        
        self.assertEqual(consulta.paciente, self.paciente_dummy)
        self.assertEqual(consulta.psicologo, self.psicologo_completo)
        self.assertEqual(consulta.data_hora_agendada, data_hora)

    def test_psicologo_filtros_form_valid(self):
        """Testa a validação básica do formulário de filtros de psicólogo."""
        form_data = {
            "valor_minimo": 50,
            "valor_maximo": 200
        }
        form = PsicologoFiltrosForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_consulta_filtros_form_valid(self):
        """Testa a validação básica do formulário de filtros de consulta."""
        form_data = {
            "estado": "SOLICITADA"
        }
        form = ConsultaFiltrosForm(
            data=form_data,
            usuario=self.paciente_dummy.usuario
        )
        self.assertTrue(form.is_valid())
