from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from terapia.models import Consulta, EstadoConsulta, TipoNotificacao, Notificacao


class AgendamentoService:
    @staticmethod
    def criar_consulta(
            paciente,
            psicologo,
            data_hora_agendada,
            estado=EstadoConsulta.SOLICITADA,
            ignorar_validacao=False
    ):
        """
        Cria uma única consulta.
        """
        consulta = Consulta(
            paciente=paciente,
            psicologo=psicologo,
            data_hora_agendada=data_hora_agendada,
            estado=estado
        )
        if not ignorar_validacao:
            consulta.full_clean()
        consulta.save()

        if estado == EstadoConsulta.SOLICITADA:
            Notificacao.objects.create(
                tipo=TipoNotificacao.CONSULTA_SOLICITADA,
                remetente=paciente.usuario,
                destinatario=psicologo.usuario,
                consulta=consulta,
            )

        return consulta

    @staticmethod
    def criar_consultas_em_lote(paciente, psicologo, slots_horarios):
        """
        Cria múltiplas consultas a partir de uma lista de horários (strings ISO ou datetimes).
        Retorna uma tupla (criadas, falhas).
        """
        tz = timezone.get_current_timezone()
        criadas = 0
        falhas = []

        with transaction.atomic():
            for slot in slots_horarios:
                try:
                    if isinstance(slot, str):
                        dt_naive = timezone.datetime.fromisoformat(slot)
                        dt = timezone.make_aware(dt_naive, tz)
                    else:
                        dt = slot

                    AgendamentoService.criar_consulta(
                        paciente=paciente,
                        psicologo=psicologo,
                        data_hora_agendada=dt
                    )
                    criadas += 1
                except ValidationError as ve:
                    falhas.append((slot, "; ".join(sum(ve.message_dict.values(), []))))
                except Exception as e:
                    falhas.append((slot, str(e)))

        return criadas, falhas


class PsicologoService:
    @staticmethod
    def obter_proxima_disponibilidade(psicologo):
        return psicologo.proxima_data_hora_agendavel

    @staticmethod
    def verificar_disponibilidade(psicologo, data_hora):
        return psicologo.esta_agendavel_em(data_hora)

    @staticmethod
    def gerar_matriz_disponibilidade(psicologo):
        return psicologo.get_matriz_disponibilidade_booleanos_em_json()

    @staticmethod
    def _tem_intervalo_onde_cabe_uma_consulta_em(psicologo, data_hora):
        return psicologo._tem_intervalo_onde_cabe_uma_consulta_em(data_hora)

    @staticmethod
    def obter_intervalos_sobrepostos(psicologo, intervalo):
        return psicologo.get_intervalos_sobrepostos(intervalo)

    @staticmethod
    def _get_datas_hora_dos_intervalos_da_mais_proxima_a_mais_distante_partindo_de(psicologo, instante):
        return psicologo._get_datas_hora_dos_intervalos_da_mais_proxima_a_mais_distante_partindo_de(instante)
