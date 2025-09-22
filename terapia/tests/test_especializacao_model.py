from django.db import IntegrityError
from django.forms import ValidationError
from terapia.models import Especializacao
from .model_test_case import ModelTestCase


class EspecializacaoModelTest(ModelTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.especializacao_1 = cls.especializacoes[0]

    def test_str_representation(self):
        self.assertEqual(str(self.especializacao_1), self.especializacao_1.titulo)

    def test_dados_corretos(self):
        especializacao = Especializacao.objects.create(
            titulo="Especialização Teste",
            descricao="Descrição da Especialização Teste"
        )
        especializacao.psicologos.set(self.psicologos_dummies)

        self.assertEqual(especializacao.titulo, "Especialização Teste")
        self.assertEqual(especializacao.descricao, "Descrição da Especialização Teste")
        self.assertQuerySetEqual(especializacao.psicologos.all(), self.psicologos_dummies, ordered=False)

    def test_impede_titulo_longo(self):
        with self.assertRaises(ValidationError) as ctx:
            max_length = Especializacao._meta.get_field("titulo").max_length

            Especializacao(
                titulo="E" * (max_length + 1), descricao="Especialização com título longo"
            ).clean_fields()

        self.assertEqual("max_length", ctx.exception.error_dict["titulo"][0].code)

    def test_impede_titulo_duplicado(self):
        with self.assertRaisesMessage(IntegrityError, "UNIQUE"):
            Especializacao.objects.create(
                titulo=self.especializacao_1.titulo,
                descricao="Especialização duplicada"
            )
