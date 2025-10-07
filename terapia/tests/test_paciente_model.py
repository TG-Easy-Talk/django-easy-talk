from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from terapia.models import Paciente
from django.db import IntegrityError
from .model_test_case import ModelTestCase


Usuario = get_user_model()


class PacienteModelTest(ModelTestCase):
    def test_str_representation(self):
        self.assertEqual(str(self.paciente_dummy), self.paciente_dummy.nome)

    def test_dados_corretos(self):
        usuario = Usuario.objects.create_user(email="usuario@example.com", password="senha123")
        paciente = Paciente.objects.create(
            usuario=usuario,
            nome='Carlos Alberto',
            cpf='987.654.321-11',
        )

        self.assertEqual(paciente.nome, 'Carlos Alberto')
        self.assertEqual(paciente.cpf, '987.654.321-11')
        self.assertEqual(paciente.usuario, usuario)
        self.assertQuerySetEqual(paciente.consultas.all(), [], ordered=False)
        self.assertIsNone(paciente.foto.name)

        consultas = self.criar_consultas_genericas(paciente=paciente, psicologo=self.psicologo_dummy)

        self.assertQuerySetEqual(paciente.consultas.all(), consultas, ordered=False)

    def test_fk_usuario_obrigatoria(self):
        with self.assertRaisesMessage(IntegrityError, "NOT NULL"):
            Paciente.objects.create(
                nome='Paciente sem usuário',
                cpf='369.720.320-75',
            )

    def test_cpf_unico(self):
        with self.assertRaisesMessage(IntegrityError, "UNIQUE"):
            Paciente.objects.create(
                usuario=self.usuario_dummy,
                nome='Maria Souza',
                cpf=self.paciente_dummy.cpf,
            )

    def test_cpf_invalido(self):
        cpfs_invalidos = [
            '574.768.960-67',
            '57476896067',
            '111.111.111-11',
            '1234567890',
            '123456789012',
            '1234567890a',
            '00000000000',
            '11111111111',
            '22222222222',
            '52998224726',
            '16899535000',
            '11144477736',
            '86288366758',
            '15350946057',
            '07068058010',
            '28625541039',
            '98765432101',
            '44784160877',
            '12787226885',
            '18803567837',
        ]

        for cpf in cpfs_invalidos:
            with self.subTest(cpf=cpf):
                with self.assertRaises(ValidationError) as ctx:
                    Paciente(
                        usuario=self.usuario_dummy,
                        nome='Paciente Inválido',
                        cpf=cpf,
                    ).full_clean()

                self.assertEqual(
                    'cpf_invalido',
                    ctx.exception.error_dict["cpf"][0].code,
                )

    def test_cpf_valido(self):
        cpfs_validos = [
            '52998224725',
            '16899535009',
            '11144477735',
            '86288366757',
            '15350946056',
            '07068058019',
            '28625541038',
            '98765432100',
            '44784160876',
            '12787226884',
            '18803567836',
            '529.982.247-25',
            '168.995.350-09',
            '111.444.777-35',
            '862.883.667-57',
        ]

        for cpf in cpfs_validos:
            with self.subTest(cpf=cpf):
                Paciente(
                    usuario=self.usuario_dummy,
                    nome='Paciente Válido',
                    cpf=cpf,
                ).full_clean()

    def test_impede_usuario_com_psicologo(self):
        with self.assertRaises(ValidationError) as ctx:
            Paciente(
                usuario=self.psicologo_dummy.usuario,
                nome='Paciente em usuário com psicólogo',
                cpf='446.753.260-99',
            ).clean_fields()

        self.assertEqual(
            "psicologo_ja_relacionado",
            ctx.exception.error_dict["usuario"][0].code,
        )

    def test_impede_usuario_com_outro_paciente(self):
        with self.assertRaises(ValidationError) as ctx:
            Paciente(
                usuario=self.paciente_dummy.usuario,
                nome='Paciente em usuário com paciente',
                cpf='963.562.490-56',
            ).validate_unique()

        self.assertEqual(
            'unique',
            ctx.exception.error_dict['usuario'][0].code
        )
