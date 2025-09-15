from datetime import datetime, time, UTC
from zoneinfo import ZoneInfo
from django.test import TestCase
from terapia.constantes import CONSULTA_ANTECEDENCIA_MINIMA, CONSULTA_DURACAO
from terapia.models import Especializacao, Paciente, Psicologo, IntervaloDisponibilidade, Consulta
from django.contrib.auth import get_user_model
from django.utils import timezone


Usuario = get_user_model()


class BaseTestCase(TestCase):
    fusos_para_teste = [
        UTC,
        timezone.get_default_timezone(),
        timezone.get_current_timezone(),
        ZoneInfo("Asia/Tokyo"),
        ZoneInfo("America/New_York"),
        ZoneInfo("Africa/Cairo"),
        ZoneInfo("Asia/Shanghai"),
        ZoneInfo("Pacific/Chatham"),
        ZoneInfo("Pacific/Marquesas"),
        ZoneInfo("Iran"),
        ZoneInfo("Australia/Eucla"),
    ] + [ZoneInfo(f"Etc/GMT{offset:+}") for offset in range(-14, 13)]
    
    @classmethod
    def setUpTestData(cls):
        cls.especializacoes = [
            Especializacao.objects.create(
                titulo=f"Especialização {i}", descricao=f"Descrição da Especialização {i}"
            ) for i in range(1, 4)
        ]

        cls.psicologo_completo = Psicologo.objects.create(
            usuario=Usuario.objects.create_user(email='psicologo.completo@example.com', password='senha123'),
            nome_completo='Psicólogo Completo',
            crp='06/54321',
            valor_consulta=100.00,
        )
        cls.psicologo_completo.especializacoes.set(cls.especializacoes)
        cls.psicologo_completo.save()
        cls.set_disponibilidade_generica(cls.psicologo_completo)

        cls.psicologo_incompleto = Psicologo.objects.create(
            usuario=Usuario.objects.create_user(email='psicologo.incompleto@example.com', password='senha123'),
            nome_completo='Psicólogo Incompleto',
            crp='03/12121',
        )

        cls.usuario_dummy = Usuario.objects.create_user(email="usuario.dummy@example.com", password="senha123")

        cls.pacientes_dummies = [
            Paciente.objects.create(
                usuario=Usuario.objects.create_user(email="paciente.dummy.1@example.com", password="senha123"),
                nome='Paciente Dummy',
                cpf='111.111.111-11'
            ),
            Paciente.objects.create(
                usuario=Usuario.objects.create_user(email="paciente.dummy.2@example.com", password="senha123"),
                nome='Paciente Dummy 2',
                cpf='222.222.222-22'
            ),
        ]

        cls.paciente_dummy = cls.pacientes_dummies[0]

        cls.psicologos_dummies = [
            Psicologo.objects.create(
                usuario=Usuario.objects.create_user(email="psicologo.dummy.1@example.com", password="senha123"),
                nome_completo='Psicólogo Dummy',
                crp='01/11111',
                valor_consulta=100.00,
            ),
            Psicologo.objects.create(
                usuario=Usuario.objects.create_user(email="psicologo.dummy.2@example.com", password="senha123"),
                nome_completo='Psicólogo Dummy 2',
                crp='01/22222',
                valor_consulta=150.00,
            )
        ]

        for psicologo in cls.psicologos_dummies:
            cls.set_disponibilidade_generica(psicologo)
            psicologo.especializacoes.set(cls.especializacoes)

        cls.psicologo_dummy = cls.psicologos_dummies[0]

        cls.psicologo_sempre_disponivel = Psicologo.objects.create(
            usuario=Usuario.objects.create_user(email="psicologo.sempre.disponivel@example.com", password="senha123"),
            nome_completo='Psicólogo Sempre Disponível',
            crp='02/11111',
            sobre_mim='Disponível 24 horas por dia.',
            valor_consulta=100.00,
        )
        cls.psicologo_sempre_disponivel.especializacoes.set(cls.especializacoes)
        cls.intervalo_de_semana_completa = IntervaloDisponibilidade.objects.criar_por_dia_semana_e_hora(
            1, time(0, 0), 1, time(0, 0), UTC, cls.psicologo_sempre_disponivel,
        )

        cls.consultas = cls.criar_consultas_genericas(cls.paciente_dummy, cls.psicologo_sempre_disponivel)

    @classmethod
    def set_disponibilidade_generica(cls, psicologo):
        intervalos = [
            (7, time(22, 0), 1, time(2, 0)),
            (1, time(8, 0), 1, time(12, 0)),
            (1, time(14, 0), 1, time(18, 0)),
            (2, time(8, 0), 2, time(12, 0)),
            (2, time(14, 0), 2, time(18, 0)),
            (3, time(8, 0), 3, time(12, 0)),
            (3, time(14, 0), 3, time(18, 0)),
            (4, time(22, 0), 4, time(23, 0)),
            (5, time(1, 0), 5, time(3, 0)),
            (6, time(23, 0), 7, time(12, 0)),
        ]

        for intervalo in intervalos:
            IntervaloDisponibilidade.objects.criar_por_dia_semana_e_hora(
                dia_semana_inicio_iso=intervalo[0],
                hora_inicio=intervalo[1],
                dia_semana_fim_iso=intervalo[2],
                hora_fim=intervalo[3],
                fuso=UTC,
                psicologo=psicologo,
            )

    @classmethod
    def criar_consultas_genericas(cls, paciente, psicologo):
        data_hora = datetime(2024, 1, 1, 10, 0, tzinfo=UTC)

        consultas = [
            Consulta.objects.create(
                paciente=paciente,
                psicologo=psicologo,
                data_hora_agendada=data_hora,
            ),
            Consulta.objects.create(
                paciente=paciente,
                psicologo=psicologo,
                data_hora_agendada=data_hora + CONSULTA_DURACAO,
            ),
        ]
        
        return consultas
    