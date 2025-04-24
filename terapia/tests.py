import datetime
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import (
    Paciente,
    Psicologo,
    Consulta,
    EstadoConsulta
)

User = get_user_model()


class PacienteModelTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.User = get_user_model()
        cls.usuario_paciente = cls.User.objects.create_user(email='paciente@example.com', password='senha123')

    def test_criar_paciente(self):
        """
        TU01-A: Inserir dados válidos.
        usuario = c1
        nome = 'Fulano'
        cpf = '79548171058'
        foto = None
        Resultado esperado: "Conta criada"
        """
        paciente = Paciente.objects.create(
            usuario=self.usuario_paciente,
            nome='João da Silva',
            cpf='123.456.789-00'
        )
        self.assertEqual(paciente.nome, 'João da Silva')
        self.assertEqual(paciente.cpf, '123.456.789-00')
        self.assertEqual(paciente.usuario, self.usuario_paciente)
        self.assertIsNone(paciente.foto.name)

    def test_cpf_unico(self):
        Paciente.objects.create(
            usuario=self.usuario_paciente,
            nome='João da Silva',
            cpf='123.456.789-00'
        )
        usuario_paciente_2 = self.User.objects.create_user(email='paciente2@example.com', password='senha123')
        with self.assertRaises(Exception) as context:
            Paciente.objects.create(
                usuario=usuario_paciente_2,
                nome='Maria Souza',
                cpf='123.456.789-00'
            )
        self.assertIn('unique constraint failed', str(context.exception).lower())

    def test_cpf_invalido(self):
        """
        TU01-B: Inserir um CPF inexistente.
        usuario = c1
        nome = 'Fulano'
        cpf = '11111111111'
        foto = None
        Resultado esperado: "Este CPF é inválido"
        """
        paciente = Paciente(
            usuario=self.usuario_paciente,
            nome='Teste Inválido',
            cpf='123'
        )
        with self.assertRaises(ValidationError) as context:
            paciente.full_clean()
        # Espera mensagem de erro no campo 'cpf'
        self.assertIn('Este CPF é inválido', context.exception.message_dict.get('cpf', []))

    def test_nome_verbose_name(self):
        self.assertEqual(Paciente._meta.get_field('nome').verbose_name, 'Nome')

    def test_cpf_verbose_name(self):
        self.assertEqual(Paciente._meta.get_field('cpf').verbose_name, 'CPF')

    def test_foto_verbose_name(self):
        self.assertEqual(Paciente._meta.get_field('foto').verbose_name, 'Foto')

    def test_meta_verbose_name(self):
        self.assertEqual(Paciente._meta.verbose_name, 'Paciente')

    def test_meta_verbose_name_plural(self):
        self.assertEqual(Paciente._meta.verbose_name_plural, 'Pacientes')

    def test_str_representation(self):
        paciente = Paciente.objects.create(
            usuario=self.usuario_paciente,
            nome='Carlos Alberto',
            cpf='987.654.321-11'
        )
        self.assertEqual(str(paciente), 'Carlos Alberto')

    def test_clean_impede_usuario_com_psicologo(self):
        usuario_psicologo = self.User.objects.create_user(email='psicologo@example.com', password='senha456')
        Psicologo.objects.create(usuario=usuario_psicologo, nome_completo='Dra. Ana Paula', crp='06/12345')
        paciente = Paciente(usuario=usuario_psicologo, nome='Novo Paciente', cpf='111.222.333-44')
        with self.assertRaises(ValidationError) as context:
            paciente.clean()
        self.assertEqual(str(context.exception), "['Este usuário já está relacionado a um psicólogo.']")


class PsicologoModelTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.User = get_user_model()
        cls.usuario_psicologo = cls.User.objects.create_user(email='psicologo@example.com', password='senha456')

    def test_criar_psicologo(self):
        """
        TU02-A: Inserir dados válidos.
        usuario = p1
        nome = 'João Silva'
        crp = '06/12345'
        foto = None
        descricao = 'Formado na Unesp com mestrado em psicologia familiar'
        duracaoConsulta = 60
        valorHora = 70.00
        disponibilidade = [...]
        Resultado esperado: "Conta criada"
        """
        psicologo = Psicologo.objects.create(
            usuario=self.usuario_psicologo,
            nome_completo='Dra. Mariana Oliveira',
            crp='06/67890'
        )
        self.assertEqual(psicologo.nome_completo, 'Dra. Mariana Oliveira')
        self.assertEqual(psicologo.crp, '06/67890')
        self.assertEqual(psicologo.usuario, self.usuario_psicologo)
        self.assertIsNone(psicologo.foto.name)
        self.assertEqual(psicologo.sobre_mim, '')
        self.assertIsNone(psicologo.valor_consulta)
        self.assertEqual(psicologo.disponibilidade, {})

    def test_crp_unico(self):
        Psicologo.objects.create(
            usuario=self.usuario_psicologo,
            nome_completo='Dra. Mariana Oliveira',
            crp='06/67890'
        )
        usuario_psicologo_2 = self.User.objects.create_user(email='psicologo2@example.com', password='senha456')
        with self.assertRaises(Exception) as context:
            Psicologo.objects.create(
                usuario=usuario_psicologo_2,
                nome_completo='Dr. Pedro Almeida',
                crp='06/67890'
            )
        self.assertIn('unique constraint failed', str(context.exception).lower())

    def test_crp_invalido(self):
        """
        TU02-B: Inserir um CRP inexistente.
        usuario = p1
        nome = 'João Silva'
        crp = '99/99999'
        foto = None
        descricao = 'Formado na Unesp com mestrado em psicologia familiar'
        duracaoConsulta = 60
        valorHora = 70.00
        disponibilidade = [...]
        Resultado esperado: "Este CRP é inválido"
        """
        psicologo = Psicologo(
            usuario=self.usuario_psicologo,
            nome_completo='Teste Inválido',
            crp='99/99999'
        )
        with self.assertRaises(ValidationError) as context:
            psicologo.full_clean()
        # Verifica se a mensagem de erro aparece no campo 'crp'
        self.assertIn(
            'Este CRP é inválido',
            context.exception.message_dict.get('crp', [])
        )

    def test_valor_consulta_min_validator(self):
        """
        TU02-C: Inserir uma duração de consulta maior que o permitido.
        duracaoConsulta = 61
        Resultado esperado: "A duração da consulta está muito longa; o tempo máximo permitido é de 1 hora."
        """
        psicologo = Psicologo(
            usuario=self.usuario_psicologo,
            nome_completo='Dr. Ricardo Gomes',
            crp='06/11223',
            valor_consulta=-10.00
        )
        with self.assertRaises(ValidationError) as context:
            psicologo.full_clean()
        self.assertIn('Ensure this value is greater than or equal to 0.',
                      context.exception.message_dict['valor_consulta'])

    def test_nome_completo_verbose_name(self):
        self.assertEqual(Psicologo._meta.get_field('nome_completo').verbose_name, 'Nome Completo')

    def test_crp_verbose_name(self):
        self.assertEqual(Psicologo._meta.get_field('crp').verbose_name, 'CRP')

    def test_valor_consulta_verbose_name(self):
        self.assertEqual(Psicologo._meta.get_field('valor_consulta').verbose_name, 'Valor da Consulta')

    def test_disponibilidade_verbose_name(self):
        self.assertEqual(Psicologo._meta.get_field('disponibilidade').verbose_name, 'Disponibilidade')

    def test_meta_verbose_name(self):
        self.assertEqual(Psicologo._meta.verbose_name, 'Psicólogo')

    def test_meta_verbose_name_plural(self):
        self.assertEqual(Psicologo._meta.verbose_name_plural, 'Psicólogos')

    def test_str_representation(self):
        psicologo = Psicologo.objects.create(
            usuario=self.usuario_psicologo,
            nome_completo='Dra. Fernanda Costa',
            crp='06/33445'
        )
        self.assertEqual(str(psicologo), 'Dra. Fernanda Costa')

    def test_clean_impede_usuario_com_paciente(self):
        usuario_paciente = self.User.objects.create_user(email='paciente2@example.com', password='senha789')
        Paciente.objects.create(usuario=usuario_paciente, nome='Laura Mendes', cpf='555.666.777-88')
        psicologo = Psicologo(usuario=usuario_paciente, nome_completo='Novo Psicólogo', crp='06/99999')
        with self.assertRaises(ValidationError) as context:
            psicologo.clean()
        self.assertEqual(str(context.exception), "['Este usuário já está relacionado a um paciente.']")


class ConsultaModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # cria usuário cliente e psicólogo
        cls.usuario_cliente = User.objects.create_user(
            email='c1@example.com', password='senha123'
        )
        cls.usuario_psicologo = User.objects.create_user(
            email='p1@example.com', password='senha123'
        )

        # instâncias de Paciente e Psicologo
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

        # garante disponibilidade ampla no dia da base_dt
        cls.base_dt = datetime.datetime(
            2025, 4, 26, 13, 30,
            tzinfo=timezone.get_current_timezone()
        )
        dia_semana = cls.base_dt.isoweekday()
        cls.psicologo.disponibilidade = [{
            "dia_semana": dia_semana,
            "intervalos": [
                {"horario_inicio": "00:00", "horario_fim": "23:59"}
            ]
        }]
        cls.psicologo.save()

        # datas auxiliares
        cls.past_dt = datetime.datetime(
            2024, 4, 26, 13, 30,
            tzinfo=timezone.get_current_timezone()
        )
        cls.unavailable_dt = datetime.datetime(
            2025, 4, 26, 3, 30,
            tzinfo=timezone.get_current_timezone()
        )

    def test_tu03_a_agendamento_valido(self):
        """
        TU03-A: Inserir dados válidos.
        dataHoraMarcada = '2025-04-26 13:30:00'
        duracao = None
        estado = 'SOLICITADA'
        Resultado esperado: "Consulta agendada"
        """
        consulta = Consulta(
            paciente=self.paciente,
            psicologo=self.psicologo,
            data_hora_marcada=self.base_dt,
            duracao=60,
            estado=EstadoConsulta.SOLICITADA
        )
        # não deve lançar
        consulta.full_clean()

    def test_tu03_b_data_passada(self):
        """
        TU03-B: Inserir data e horário passados.
        dataHoraMarcada = '2024-04-26 13:30:00'
        Resultado esperado: "A consulta deve ser agendada para uma data futura"
        """
        consulta = Consulta(
            paciente=self.paciente,
            psicologo=self.psicologo,
            data_hora_marcada=self.past_dt,
            duracao=60,
            estado=EstadoConsulta.SOLICITADA
        )
        with self.assertRaises(ValidationError) as cm:
            consulta.full_clean()
        self.assertIn("data futura", str(cm.exception))

    def test_tu03_c_psicologo_indisponivel(self):
        """
        TU03-C: Inserir data e horário em que o psicólogo está indisponível.
        dataHoraMarcada = '2025-04-26 03:30:00'
        Resultado esperado: "O psicólogo não tem disponibilidade nessa data e horário"
        """
        # restringe disponibilidade para não incluir 03:30
        dia_semana = self.unavailable_dt.isoweekday()
        self.psicologo.disponibilidade = [{
            "dia_semana": dia_semana,
            "intervalos": [{"horario_inicio": "09:00", "horario_fim": "17:00"}]
        }]
        self.psicologo.save()

        consulta = Consulta(
            paciente=self.paciente,
            psicologo=self.psicologo,
            data_hora_marcada=self.unavailable_dt,
            duracao=60,
            estado=EstadoConsulta.SOLICITADA
        )
        with self.assertRaises(ValidationError) as cm:
            consulta.full_clean()
        self.assertIn("não tem disponibilidade", str(cm.exception))

    def test_tu03_d_estado_nao_solicitada(self):
        """
        TU03-D: Criar uma consulta nova em um estado que não seja o inicial ("SOLICITADA").
        Resultado esperado: "A consulta deve ser sempre instanciada como 'SOLICITADA'"
        """
        consulta = Consulta(
            paciente=self.paciente,
            psicologo=self.psicologo,
            data_hora_marcada=self.base_dt,
            duracao=60,
            estado=EstadoConsulta.CONFIRMADA
        )
        with self.assertRaises(ValidationError) as cm:
            consulta.full_clean()
        self.assertIn("instanciada como 'SOLICITADA'", str(cm.exception))

    def test_tu03_e_conflito_agendamento(self):
        """
        TU03-E: Inserir data e horário em que o cliente já tem alguma consulta agendada.
        Resultado esperado: "Você já possui uma consulta agendada nesse horário"
        """
        Consulta.objects.create(
            paciente=self.paciente,
            psicologo=self.psicologo,
            data_hora_marcada=self.base_dt,
            duracao=60
        )
        # tenta agendar de novo
        dup = Consulta(
            paciente=self.paciente,
            psicologo=self.psicologo,
            data_hora_marcada=self.base_dt,
            duracao=60
        )
        with self.assertRaises(ValidationError) as cm:
            dup.full_clean()
        self.assertIn("já possui uma consulta agendada", str(cm.exception))
