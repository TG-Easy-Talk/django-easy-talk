from terapia.constantes import CONSULTA_DURACAO
from .model_test_case import ModelTestCase
from datetime import timedelta


class BasePacienteOuPsicologoModelTest(ModelTestCase):
    def test_ja_tem_consulta_em(self):
        envolvidos = [self.paciente_dummy, self.psicologo_sempre_disponivel]
        consultas = self.get_consultas_genericas()

        for envolvido in envolvidos:
            self.assertFalse(envolvido.ja_tem_consulta_em(consultas[0].data_hora_agendada - CONSULTA_DURACAO))
            self.assertTrue(envolvido.ja_tem_consulta_em(consultas[0].data_hora_agendada - CONSULTA_DURACAO + timedelta(minutes=1)))
            self.assertTrue(envolvido.ja_tem_consulta_em(consultas[0].data_hora_agendada))
            self.assertTrue(envolvido.ja_tem_consulta_em(consultas[1].data_hora_agendada))
            self.assertTrue(envolvido.ja_tem_consulta_em(consultas[1].data_hora_agendada + CONSULTA_DURACAO - timedelta(minutes=1)))
            self.assertFalse(envolvido.ja_tem_consulta_em(consultas[1].data_hora_agendada + CONSULTA_DURACAO))
