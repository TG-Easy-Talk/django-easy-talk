from django.db import IntegrityError
from django.forms import ValidationError
from django.test import TestCase
from django.contrib.auth import get_user_model
from terapia.models import Especializacao, Psicologo


Usuario = get_user_model()


class EspecializacaoModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.especializacoes = [
            Especializacao.objects.create(
                titulo=f"Especialização {i}", descricao=f"Descrição da Especialização {i}"
            ) for i in range(1, 4)
        ]
        cls.especializacao_1 = cls.especializacoes[0]

        cls.psicologos = [
            Psicologo.objects.create(
                usuario=Usuario.objects.create_user(email="psicologo1@example.com", password="senha123"),
                nome_completo='Psicólogo 1',
                crp='06/12345',
            ),
            Psicologo.objects.create(
                usuario=Usuario.objects.create_user(email="psicologo2@example.com", password="senha123"),
                nome_completo='Psicólogo 2',
                crp='06/12346',
            ),
        ]

        for psicologo in cls.psicologos:
            psicologo.especializacoes.set(cls.especializacoes)
            psicologo.save()

    def test_str_representation(self):
        self.assertEqual(str(self.especializacao_1), self.especializacao_1.titulo)

    def test_dados_corretos(self):
        self.assertEqual(self.especializacao_1.titulo, "Especialização 1")
        self.assertEqual(self.especializacao_1.descricao, "Descrição da Especialização 1")
        self.assertQuerySetEqual(self.especializacao_1.psicologos.all(), self.psicologos, ordered=False)

    def test_impede_titulo_longo(self):
        with self.assertRaises(ValidationError) as ctx:
            Especializacao(
                titulo="E" * 51, descricao="Especialização com título longo"
            ).full_clean()

        self.assertEqual("max_length", ctx.exception.error_dict["titulo"][0].code)

    def test_impede_titulo_duplicado(self):
        with self.assertRaisesMessage(IntegrityError, "UNIQUE"):
            Especializacao.objects.create(
                titulo=self.especializacao_1.titulo,
                descricao="Especialização duplicada"
            )
