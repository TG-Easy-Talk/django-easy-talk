from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from .models import Paciente, Psicologo


class PacienteModelTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.User = get_user_model()
        cls.usuario_paciente = cls.User.objects.create_user(email='paciente@example.com', password='senha123')

    def test_criar_paciente(self):
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
        # TU01-B: CPF inexistente/formato inválido deve gerar ValidationError
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

    def test_valor_consulta_min_validator(self):
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
