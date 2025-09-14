from datetime import time, UTC, timedelta
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth import get_user_model
from freezegun import freeze_time
from terapia.constantes import CONSULTA_ANTECEDENCIA_MAXIMA, CONSULTA_ANTECEDENCIA_MINIMA, CONSULTA_DURACAO
from terapia.models import Especializacao, Paciente, Psicologo, Consulta, IntervaloDisponibilidade, EstadoConsulta


Usuario = get_user_model()


class ConsultaModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.especializacoes = [
            Especializacao.objects.create(
                titulo=f"Especialização {i}", descricao=f"Descrição da Especialização {i}"
            ) for i in range(1, 4)
        ]
        cls.paciente = Paciente.objects.create(
            usuario=Usuario.objects.create_user(email="paciente@example.com", password="senha123"),
            nome='Paciente',
            cpf='12345678901'
        )
        cls.psicologo_completo = Psicologo.objects.create(
            usuario=Usuario.objects.create_user(email='psicologo.completo@example.com', password='senha123'),
            nome_completo='Psicólogo Completo',
            crp='06/54321',
            valor_consulta=100.00,
        )
        cls.psicologo_incompleto = Psicologo.objects.create(
            usuario=Usuario.objects.create_user(email='psicologo.incompleto@example.com', password='senha123'),
            nome_completo='Psicólogo Incompleto',
            crp='03/12121',
        )
        IntervaloDisponibilidade.objects.criar_por_dia_semana_e_hora(
            1, time(0, 0), 1, time(0, 0), UTC, cls.psicologo_completo,
        )
        cls.psicologo_completo.especializacoes.set(cls.especializacoes)
        cls.psicologo_completo.save()

        cls.agora = timezone.now()

        with freeze_time(cls.agora):
            cls.consultas = [
                Consulta.objects.create(
                    paciente=cls.paciente,
                    psicologo=cls.psicologo_completo,
                    data_hora_agendada=cls.agora + CONSULTA_ANTECEDENCIA_MINIMA,
                ),
                Consulta.objects.create(
                    paciente=cls.paciente,
                    psicologo=cls.psicologo_completo,
                    data_hora_agendada=cls.agora + CONSULTA_ANTECEDENCIA_MINIMA + CONSULTA_DURACAO,
                    anotacoes="Paciente explicou o que está passando",
                    checklist_tarefas="1. Fazer exercícios de respiração, 2. Praticar exercício",
                    estado=EstadoConsulta.EM_ANDAMENTO,
                    duracao=timedelta(minutes=45),
                ),
            ]

    def test_str_representation(self):
        self.assertEqual(str(self.consultas[0]), f"Consulta SOLICITADA agendada para {timezone.localtime(self.consultas[0].data_hora_agendada):%d/%m/%Y %H:%M} com Paciente e Psicólogo Completo")

    def test_dados_corretos(self):
        self.assertEqual(self.consultas[0].paciente, self.paciente)
        self.assertEqual(self.consultas[0].psicologo, self.psicologo_completo)
        self.assertEqual(self.consultas[0].data_hora_solicitada, self.agora)
        self.assertEqual(self.consultas[0].data_hora_agendada, self.agora + CONSULTA_ANTECEDENCIA_MINIMA)
        self.assertIsNone(self.consultas[0].anotacoes)
        self.assertIsNone(self.consultas[0].checklist_tarefas)
        self.assertEqual(self.consultas[0].estado, EstadoConsulta.SOLICITADA)
        self.assertIsNone(self.consultas[0].duracao)
        
        self.assertEqual(self.consultas[1].paciente, self.paciente)
        self.assertEqual(self.consultas[1].psicologo, self.psicologo_completo)
        self.assertEqual(self.consultas[1].data_hora_solicitada, self.agora)
        self.assertEqual(self.consultas[1].data_hora_agendada, self.agora + CONSULTA_ANTECEDENCIA_MINIMA + CONSULTA_DURACAO)
        self.assertEqual(self.consultas[1].anotacoes, "Paciente explicou o que está passando")
        self.assertEqual(self.consultas[1].checklist_tarefas, "1. Fazer exercícios de respiração, 2. Praticar exercício")
        self.assertEqual(self.consultas[1].estado, EstadoConsulta.EM_ANDAMENTO)
        self.assertEqual(self.consultas[1].duracao, timedelta(minutes=45))

    def test_impede_psicologo_incompleto(self):
        with self.assertRaises(ValidationError) as ctx:
            Consulta(
                paciente=self.paciente,
                psicologo=self.psicologo_incompleto,
                data_hora_agendada=self.agora + CONSULTA_ANTECEDENCIA_MINIMA,
            ).full_clean()

        self.assertEqual("invalid", ctx.exception.error_dict["psicologo"][0].code)

    def test_segundos_e_microssegundos_sao_desprezados(self):
        consulta = None

        with freeze_time(self.agora):
            consulta = Consulta(
                paciente=self.paciente,
                psicologo=self.psicologo_completo,
                data_hora_agendada=self.agora.replace(second=30, microsecond=500) + timedelta(weeks=1),
            )
            consulta.clean()
            consulta.save()

        self.assertEqual(consulta.data_hora_agendada.second, 0)
        self.assertEqual(consulta.data_hora_agendada.microsecond, 0)

    def test_impede_psicologo_nao_disponivel(self):
        with freeze_time(self.agora):
            with self.assertRaises(ValidationError) as ctx:
                Consulta(
                    paciente=self.paciente,
                    psicologo=self.psicologo_completo,
                    data_hora_agendada=self.consultas[0].data_hora_agendada,
                ).clean()

            self.assertEqual("psicologo_nao_disponivel", ctx.exception.error_dict["data_hora_agendada"][0].code)

    def test_impede_paciente_nao_disponivel(self):
        with freeze_time(self.agora):
            psicologo_novo = Psicologo.objects.create(
                usuario=Usuario.objects.create_user(email="psicologo_novo", password="senha123"),
                nome_completo="Psicólogo Novo",
                crp="01/12412",
            )
            IntervaloDisponibilidade.objects.criar_por_dia_semana_e_hora(
                1, time(0, 0), 1, time(0, 0), UTC, psicologo_novo,
            )

            with self.assertRaises(ValidationError) as ctx:
                Consulta(
                    paciente=self.paciente,
                    psicologo=psicologo_novo,
                    data_hora_agendada=self.consultas[1].data_hora_agendada,
                ).clean()

            self.assertEqual("paciente_nao_disponivel", ctx.exception.error_dict["data_hora_agendada"][0].code)

    def test_antecedencia_minima(self):
        with freeze_time(self.agora):
            with self.assertRaises(ValidationError) as ctx:
                Consulta(
                    paciente=self.paciente,
                    psicologo=self.psicologo_completo,
                    data_hora_agendada=self.agora + CONSULTA_ANTECEDENCIA_MINIMA - timedelta(minutes=1),
                ).clean_fields()

            self.assertEqual("antecedencia_minima_nao_atendida", ctx.exception.error_dict["data_hora_agendada"][0].code)

    def test_antecedencia_maxima(self):
        with freeze_time(self.agora):
            with self.assertRaises(ValidationError) as ctx:
                Consulta(
                    paciente=self.paciente,
                    psicologo=self.psicologo_completo,
                    data_hora_agendada=self.agora + CONSULTA_ANTECEDENCIA_MAXIMA + timedelta(minutes=1),
                ).clean_fields()

            self.assertEqual("antecedencia_maxima_nao_atendida", ctx.exception.error_dict["data_hora_agendada"][0].code)

    def test_divisivel_por_duracao_consulta(self):
        with freeze_time(self.agora):
            with self.assertRaises(ValidationError) as ctx:
                Consulta(
                    paciente=self.paciente,
                    psicologo=self.psicologo_completo,
                    data_hora_agendada=self.agora + CONSULTA_ANTECEDENCIA_MINIMA + timedelta(minutes=15),
                ).clean_fields()

            self.assertEqual("data_hora_nao_divisivel_por_duracao_consulta", ctx.exception.error_dict["data_hora_agendada"][0].code)
    