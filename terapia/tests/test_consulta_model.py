from datetime import datetime, UTC, timedelta
from django.core.exceptions import ValidationError
from django.utils import timezone
from freezegun import freeze_time
from terapia.constantes import CONSULTA_ANTECEDENCIA_MAXIMA, CONSULTA_ANTECEDENCIA_MINIMA
from terapia.models import Consulta, EstadoConsulta
from .model_test_case import ModelTestCase


class ConsultaModelTest(ModelTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.agora_fake = datetime(2022, 1, 1, 10, 0, tzinfo=UTC)

    def test_str_representation(self):
        consulta = Consulta.objects.create(
            data_hora_agendada=datetime(2023, 12, 1, 10, 0, tzinfo=UTC),
            paciente=self.paciente_dummy,
            psicologo=self.psicologo_sempre_disponivel,
        )
        
        with timezone.override(UTC):
            self.assertEqual(str(consulta), f"Consulta SOLICITADA agendada para 01/12/2023 10:00 (UTC) com Paciente Dummy e Psicólogo Sempre Disponível")

    def test_dados_corretos(self):
        data_hora_agendada = datetime(2023, 1, 1, 10, 0, tzinfo=UTC)
        consulta = None

        with freeze_time(self.agora_fake):
            consulta = Consulta.objects.create(
                paciente=self.paciente_dummy,
                psicologo=self.psicologo_sempre_disponivel,
                data_hora_agendada=data_hora_agendada,
            )

        self.assertEqual(consulta.data_hora_solicitada, self.agora_fake)
        self.assertEqual(consulta.paciente, self.paciente_dummy)
        self.assertEqual(consulta.psicologo, self.psicologo_sempre_disponivel)
        self.assertEqual(consulta.data_hora_agendada, data_hora_agendada)
        self.assertIsNone(consulta.anotacoes)
        self.assertIsNone(consulta.checklist_tarefas)
        self.assertEqual(consulta.estado, EstadoConsulta.SOLICITADA)
        self.assertIsNone(consulta.duracao)

        anotacoes = "Paciente explicou o que está passando"
        checklist_tarefas = "1. Fazer exercícios de respiração, 2. Praticar exercício"
        duracao = timedelta(minutes=45)
        estado = EstadoConsulta.EM_ANDAMENTO

        with freeze_time(self.agora_fake):
            consulta = Consulta.objects.create(
                paciente=self.paciente_dummy,
                psicologo=self.psicologo_sempre_disponivel,
                data_hora_agendada=data_hora_agendada,
                anotacoes=anotacoes,
                checklist_tarefas=checklist_tarefas,
                estado=estado,
                duracao=duracao,
            )
        
        self.assertEqual(consulta.data_hora_solicitada, self.agora_fake)
        self.assertEqual(consulta.paciente, self.paciente_dummy)
        self.assertEqual(consulta.psicologo, self.psicologo_sempre_disponivel)
        self.assertEqual(consulta.data_hora_agendada, data_hora_agendada)
        self.assertEqual(consulta.anotacoes, anotacoes)
        self.assertEqual(consulta.checklist_tarefas, checklist_tarefas)
        self.assertEqual(consulta.estado, estado)
        self.assertEqual(consulta.duracao, duracao)

    def test_impede_psicologo_incompleto(self):
        with self.assertRaises(ValidationError) as ctx:
            Consulta(
                paciente=self.paciente_dummy,
                psicologo=self.psicologo_incompleto,
                data_hora_agendada=self.agora_fake,
            ).clean_fields()

        self.assertEqual("invalid", ctx.exception.error_dict["psicologo"][0].code)

    def test_segundos_e_microssegundos_sao_desprezados(self):
        consulta = None

        with freeze_time(self.agora_fake):
            consulta = Consulta(
                paciente=self.paciente_dummy,
                psicologo=self.psicologo_sempre_disponivel,
                data_hora_agendada=self.psicologo_sempre_disponivel.proxima_data_hora_agendavel.replace(second=30, microsecond=123456)
            )
            consulta.clean()
            consulta.save()

        self.assertEqual(consulta.data_hora_agendada.second, 0)
        self.assertEqual(consulta.data_hora_agendada.microsecond, 0)

    def test_impede_psicologo_nao_disponivel(self):
        with freeze_time(self.agora_fake):
            with self.assertRaises(ValidationError) as ctx:
                consulta_que_ocupa_o_psicologo = Consulta.objects.create(
                    paciente=self.paciente_dummy,
                    psicologo=self.psicologo_sempre_disponivel,
                    data_hora_agendada=self.psicologo_sempre_disponivel.proxima_data_hora_agendavel,
                )

                Consulta(
                    paciente=self.pacientes_dummies[1],
                    psicologo=self.psicologo_sempre_disponivel,
                    data_hora_agendada=consulta_que_ocupa_o_psicologo.data_hora_agendada,
                ).clean()

            self.assertEqual("psicologo_nao_disponivel", ctx.exception.error_dict["data_hora_agendada"][0].code)

    def test_impede_paciente_nao_disponivel(self):
        with freeze_time(self.agora_fake):
            with self.assertRaises(ValidationError) as ctx:
                consulta_que_ocupa_o_paciente = Consulta.objects.create(
                    paciente=self.paciente_dummy,
                    psicologo=self.psicologos_dummies[0],
                    data_hora_agendada=self.psicologos_dummies[0].proxima_data_hora_agendavel,
                )

                Consulta(
                    paciente=self.paciente_dummy,
                    psicologo=self.psicologos_dummies[1],
                    data_hora_agendada=consulta_que_ocupa_o_paciente.data_hora_agendada,
                ).clean()

            self.assertEqual("paciente_nao_disponivel", ctx.exception.error_dict["data_hora_agendada"][0].code)

    def test_antecedencia_minima(self):
        with freeze_time(self.agora_fake):
            with self.assertRaises(ValidationError) as ctx:
                Consulta(
                    paciente=self.paciente_dummy,
                    psicologo=self.psicologo_sempre_disponivel,
                    data_hora_agendada=self.agora_fake + CONSULTA_ANTECEDENCIA_MINIMA - timedelta(microseconds=1),
                ).clean_fields()

            self.assertEqual("antecedencia_minima_nao_atendida", ctx.exception.error_dict["data_hora_agendada"][0].code)

    def test_antecedencia_maxima(self):
        with freeze_time(self.agora_fake):
            with self.assertRaises(ValidationError) as ctx:
                Consulta(
                    paciente=self.paciente_dummy,
                    psicologo=self.psicologo_sempre_disponivel,
                    data_hora_agendada=self.agora_fake + CONSULTA_ANTECEDENCIA_MAXIMA + timedelta(microseconds=1),
                ).clean_fields()

            self.assertEqual("antecedencia_maxima_nao_atendida", ctx.exception.error_dict["data_hora_agendada"][0].code)

    def test_data_hora_agendada_divisivel_por_duracao_consulta(self):
        with freeze_time(self.data_hora_nao_divisivel_por_duracao_consulta - CONSULTA_ANTECEDENCIA_MINIMA):
            with self.assertRaises(ValidationError) as ctx:
                Consulta(
                    paciente=self.paciente_dummy,
                    psicologo=self.psicologo_completo,
                    data_hora_agendada=self.data_hora_nao_divisivel_por_duracao_consulta,
                ).clean_fields()

            self.assertEqual("data_hora_nao_divisivel_por_duracao_consulta", ctx.exception.error_dict["data_hora_agendada"][0].code)
    