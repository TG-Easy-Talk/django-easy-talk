from django.core.files import File
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from .models import Paciente, Psicologo

User = get_user_model()

class PacienteModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        """
        Arrange: cria um usuário padrão para os testes de Paciente.
        """
        cls.usuario = User.objects.create_user(
            email='paciente@example.com',
            password='senha456'
        )
        cls.foto = SimpleUploadedFile(
            name='teste.jpg',
            content=b'file_content',
            content_type='image/jpeg'
        )

    def test_criar_paciente_valido(self):
        """
        Arrange: instancia Paciente com dados válidos.
        Act: full_clean() + save().
        Assert: campos persistidos corretamente, foto default None.
        """
        paciente = Paciente(
            usuario=self.usuario,
            nome='João da Silva',
            cpf='123.456.789-00',
            foto=None,
        )
        paciente.full_clean()
        paciente.save()

        self.assertEqual(paciente.nome, 'João da Silva')
        self.assertEqual(paciente.cpf, '123.456.789-00')
        self.assertEqual(paciente.usuario, self.usuario)
        self.assertIsNone(paciente.foto)

    def test_criar_paciente_valido_com_foto(self):
        """
        Arrange: instancia Paciente com dados válidos.
        Act: full_clean() + save().
        Assert: campos persistidos corretamente, foto default None.
        """
        paciente = Paciente(
            usuario=self.usuario,
            nome='João da Silva',
            cpf='123.456.789-00',
            foto=self.foto,
        )
        paciente.full_clean()
        paciente.save()

        self.assertEqual(paciente.nome, 'João da Silva')
        self.assertEqual(paciente.cpf, '123.456.789-00')
        self.assertEqual(paciente.usuario, self.usuario)
        self.assertIsNotNone(paciente.foto)
        paciente.foto.delete(save=False)

    def test_cpf_unico_raises_integrity_error(self):
        """
        Arrange: salva um Paciente com determinado CPF.
        Act & Assert: ao tentar salvar outro com mesmo CPF, IntegrityError.
        """
        Paciente.objects.create(
            usuario=self.usuario,
            nome='João da Silva',
            cpf='123.456.789-00'
        )
        outro_usuario = User.objects.create_user(
            email='paciente2@example.com',
            password='senha123'
        )
        paciente2 = Paciente(
            usuario=outro_usuario,
            nome='Maria Souza',
            cpf='123.456.789-00'
        )
        with self.assertRaisesMessage(IntegrityError, 'unique'):
            paciente2.save()

    def test_verbose_names_and_str(self):
        """
        Verifica verbose_name dos campos e __str__.
        """
        self.assertEqual(Paciente._meta.get_field('nome').verbose_name, 'Nome')
        self.assertEqual(Paciente._meta.get_field('cpf').verbose_name, 'CPF')
        self.assertEqual(Paciente._meta.get_field('foto').verbose_name, 'Foto')
        self.assertEqual(Paciente._meta.verbose_name, 'Paciente')
        self.assertEqual(Paciente._meta.verbose_name_plural, 'Pacientes')

        paciente = Paciente(
            usuario=self.usuario,
            nome='Carlos Alberto',
            cpf='987.654.321-11'
        )
        self.assertEqual(str(paciente), 'Carlos Alberto')

    def test_clean_impede_usuario_com_psicologo(self):
        """
        Arrange: cria usuário que já tem Psicologo associado.
        Act & Assert: clean() lança ValidationError.
        """
        usuario_psic = User.objects.create_user(
            email='psicologo@example.com',
            password='senha456'
        )
        Psicologo.objects.create(
            usuario=usuario_psic,
            nome_completo='Dra. Ana Paula',
            crp='06/12345'
        )
        paciente = Paciente(
            usuario=usuario_psic,
            nome='Novo Paciente',
            cpf='111.222.333-44'
        )
        with self.assertRaisesMessage(ValidationError, 'Este usuário já está relacionado a um psicólogo.'):
            paciente.clean()


class PsicologoModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        """
        Arrange: cria um usuário padrão para os testes de Psicologo.
        """
        cls.usuario = User.objects.create_user(
            email='psicologo@example.com',
            password='senha789'
        )

    def test_criar_psicologo_valido(self):
        """
        Arrange: instancia Psicologo com dados válidos.
        Act: full_clean() + save().
        Assert: campos persistidos, defaults corretos.
        """
        psic = Psicologo(
            usuario=self.usuario,
            nome_completo='Dra. Mariana Oliveira',
            crp='06/67890'
        )
        psic.full_clean()
        psic.save()

        self.assertEqual(psic.nome_completo, 'Dra. Mariana Oliveira')
        self.assertEqual(psic.crp, '06/67890')
        self.assertEqual(psic.usuario, self.usuario)
        self.assertIsNone(psic.foto)
        self.assertEqual(psic.sobre_mim, '')
        self.assertIsNone(psic.valor_consulta)
        self.assertEqual(psic.disponibilidade, {})

    def test_crp_unico_raises_integrity_error(self):
        """
        Arrange: salva um Psicologo com determinado CRP.
        Act & Assert: ao tentar salvar outro com mesmo CRP, IntegrityError.
        """
        Psicologo.objects.create(
            usuario=self.usuario,
            nome_completo='Dra. Mariana Oliveira',
            crp='06/67890'
        )
        outro_usuario = User.objects.create_user(
            email='psicologo2@example.com',
            password='senha456'
        )
        psic2 = Psicologo(
            usuario=outro_usuario,
            nome_completo='Dr. Pedro Almeida',
            crp='06/67890'
        )
        with self.assertRaisesMessage(IntegrityError, 'unique'):
            psic2.save()

    def test_valor_consulta_min_validator(self):
        """
        Arrange: atribui valor_consulta negativo.
        Act & Assert: full_clean() levanta ValidationError com mensagem de MinValueValidator.
        """
        psic = Psicologo(
            usuario=self.usuario,
            nome_completo='Dr. Ricardo Gomes',
            crp='06/11223',
            valor_consulta=-10.00
        )
        with self.assertRaisesRegex(ValidationError, 'greater than or equal to 0'):
            psic.full_clean()

    def test_verbose_names_and_str(self):
        """
        Verifica verbose_name dos campos e __str__.
        """
        self.assertEqual(Psicologo._meta.get_field('nome_completo').verbose_name, 'Nome Completo')
        self.assertEqual(Psicologo._meta.get_field('crp').verbose_name, 'CRP')
        self.assertEqual(Psicologo._meta.get_field('valor_consulta').verbose_name, 'Valor da Consulta')
        self.assertEqual(Psicologo._meta.get_field('disponibilidade').verbose_name, 'Disponibilidade')
        self.assertEqual(Psicologo._meta.verbose_name, 'Psicólogo')
        self.assertEqual(Psicologo._meta.verbose_name_plural, 'Psicólogos')

        psic = Psicologo(
            usuario=self.usuario,
            nome_completo='Dra. Fernanda Costa',
            crp='06/33445'
        )
        self.assertEqual(str(psic), 'Dra. Fernanda Costa')

    def test_clean_impede_usuario_com_paciente(self):
        """
        Arrange: cria usuário que já tem Paciente associado.
        Act & Assert: clean() lança ValidationError.
        """
        usuario_pac = User.objects.create_user(
            email='paciente2@example.com',
            password='senha789'
        )
        Paciente.objects.create(
            usuario=usuario_pac,
            nome='Laura Mendes',
            cpf='555.666.777-88'
        )
        psic = Psicologo(
            usuario=usuario_pac,
            nome_completo='Novo Psicólogo',
            crp='06/99999'
        )
        with self.assertRaisesMessage(ValidationError, 'Este usuário já está relacionado a um paciente.'):
            psic.clean()


class DocumentoFormatValidationTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = User.objects.create_user(email='user@example.com', password='senha')

    def test_formatos_cpf_invalidos(self):
        """
        Testa diversos CPFs fora do padrão: curtos, longos, letras, sem máscara e repetidos.
        """
        invalid_cpfs = [
            '123.456.78-00',  # curto
            '123.456.789-000',  # longo
            'ABC.DEF.GHI-JK',  # letras
            '12345678900',  # sem máscara
            '111.111.111-11',  # repetido
        ]
        for cpf in invalid_cpfs:
            with self.subTest(cpf=cpf):
                paciente = Paciente(
                    usuario=self.usuario,
                    nome='Teste CPF',
                    cpf=cpf
                )
                with self.assertRaises(ValidationError):
                    paciente.full_clean()

    def test_formatos_crp_invalidos(self):
        """
        Testa diversos CRPs fora do padrão: estado inválido, dígitos faltando, espaços, caracteres errados.
        """
        invalid_crps = [
            '99/12345',  # estado inválido
            '06/1234',  # dígitos faltando
            '06/ 12345',  # espaço extra depois da barra
            ' 06/12345',  # espaço no início
            '06-12345',  # caractere errado
            '06/12A45',  # letra misturada
        ]
        for crp in invalid_crps:
            with self.subTest(crp=crp):
                psic = Psicologo(
                    usuario=self.usuario,
                    nome_completo='Teste CRP',
                    crp=crp
                )
                with self.assertRaises(ValidationError):
                    psic.full_clean()