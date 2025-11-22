"""
Agendamento Service - Business logic for availability and scheduling.

This service centralizes all logic related to psychologist availability
and appointment scheduling, removing it from the Psicologo model.
"""
from typing import Optional, List
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Q

from terapia.constantes import (
    CONSULTA_DURACAO,
    CONSULTA_ANTECEDENCIA_MINIMA,
    CONSULTA_ANTECEDENCIA_MAXIMA,
)
from terapia.utilidades.geral import (
    converter_dia_semana_iso_com_hora_para_data_hora,
    desprezar_segundos_e_microssegundos,
)
from terapia.models import EstadoConsulta


class AgendamentoService:
    """
    Service responsável por toda lógica de disponibilidade e agendamento.
    Separa business logic dos models (Single Responsibility Principle).
    """
    
    @staticmethod
    def calcular_proxima_disponibilidade(psicologo) -> Optional[datetime]:
        """
        Calcula a próxima data-hora disponível para agendamento com o psicólogo.
        
        Esta lógica foi movida de Psicologo.proxima_data_hora_agendavel.
        
        Args:
            psicologo: Instância de Psicologo
            
        Returns:
            datetime: Próxima data-hora disponível ou None se não houver
        """
        if not psicologo.disponibilidade.exists():
            return None

        semanas = 0
        tempo_decorrido = timedelta(0)
        agora = timezone.localtime()
        agora_convertido = converter_dia_semana_iso_com_hora_para_data_hora(
            agora.isoweekday(), agora.time(), agora.tzinfo
        )
        datas_hora_ordenadas = AgendamentoService._get_datas_hora_dos_intervalos_da_mais_proxima_a_mais_distante_partindo_de(
            psicologo, agora
        )

        while True:
            for data_hora in datas_hora_ordenadas:
                esta_na_outra_semana = data_hora <= agora_convertido

                if esta_na_outra_semana:
                    data_hora += timedelta(weeks=1)

                data_hora += timedelta(weeks=semanas)
                tempo_decorrido = data_hora - agora_convertido

                if tempo_decorrido > CONSULTA_ANTECEDENCIA_MAXIMA:
                    return None

                data_hora_inicio = desprezar_segundos_e_microssegundos(agora + tempo_decorrido)

                if (
                    data_hora_inicio >= agora + CONSULTA_ANTECEDENCIA_MINIMA and
                    not psicologo.ja_tem_consulta_em(data_hora_inicio)
                ):
                    return data_hora_inicio
                
            semanas += 1
    
    @staticmethod
    def verificar_disponibilidade(psicologo, data_hora: datetime) -> bool:
        """
        Verifica se o psicólogo está disponível para agendamento na data-hora especificada.
        
        Esta lógica foi movida de Psicologo.esta_agendavel_em.
        
        Args:
            psicologo: Instância de Psicologo
            data_hora: Data-hora para verificar disponibilidade (em qualquer timezone)
            
        Returns:
            bool: True se disponível, False caso contrário
        """
        # CORREÇÃO: Normalizar data_hora para timezone local antes de verificar
        # Isso garante que isoweekday() e time() sejam consistentes com os intervalos
        data_hora_local = timezone.localtime(data_hora)
        
        agora = timezone.now()
        proxima_data_hora_agendavel = AgendamentoService.calcular_proxima_disponibilidade(psicologo)
        
        return bool(
            psicologo.disponibilidade.exists() and
            proxima_data_hora_agendavel is not None and
            proxima_data_hora_agendavel <= data_hora <= agora + CONSULTA_ANTECEDENCIA_MAXIMA and
            AgendamentoService._tem_intervalo_onde_cabe_uma_consulta_em(psicologo, data_hora_local) and
            not psicologo.ja_tem_consulta_em(data_hora)
        )
    
    @staticmethod
    def _get_datas_hora_dos_intervalos_da_mais_proxima_a_mais_distante_partindo_de(psicologo, instante):
        """
        Retorna as datas e horas dos intervalos de disponibilidade do psicólogo na ordem
        do mais próximo ao mais distante partindo de um instante no tempo.
        """
        instante_convertido = converter_dia_semana_iso_com_hora_para_data_hora(
            instante.isoweekday(),
            instante.time(),
            instante.tzinfo,
        )
        
        datas_hora_essa_semana = []
        datas_hora_proxima_semana = []

        for intervalo in psicologo.disponibilidade.all():
            for data_hora in intervalo.get_datas_hora():
                if data_hora >= instante_convertido + CONSULTA_ANTECEDENCIA_MINIMA:
                    datas_hora_essa_semana.append(data_hora)
                else:
                    datas_hora_proxima_semana.append(data_hora)

        datas_hora_ordenadas = sorted(datas_hora_essa_semana) + sorted(datas_hora_proxima_semana)
        return datas_hora_ordenadas
    
    @staticmethod
    def _tem_intervalo_onde_cabe_uma_consulta_em(psicologo, data_hora):
        """
        Verifica se o psicólogo tem um intervalo de disponibilidade no qual se
        encaixa uma consulta que começa na data-hora enviada.
        """
        from django.db.models import F
        
        data_hora_inicio = converter_dia_semana_iso_com_hora_para_data_hora(
            data_hora.isoweekday(),
            data_hora.time(),
            data_hora.tzinfo,
        )
        data_hora_fim = data_hora_inicio + CONSULTA_DURACAO
        data_hora_fim = converter_dia_semana_iso_com_hora_para_data_hora(
            data_hora_fim.isoweekday(),
            data_hora_fim.time(),
            data_hora_fim.tzinfo,
        )

        consulta_vira_a_semana = data_hora_fim <= data_hora_inicio

        intervalo_de_semana_completa = psicologo.disponibilidade.filter(data_hora_inicio=F("data_hora_fim"))
        intervalos_que_nao_viram_a_semana = psicologo.disponibilidade.filter(data_hora_inicio__lt=F("data_hora_fim"))
        intervalo_que_vira_a_semana = psicologo.disponibilidade.filter(data_hora_fim__lt=F("data_hora_inicio"))

        if intervalo_de_semana_completa.exists():
            return True

        if data_hora_inicio == data_hora_fim:
            return False

        if not consulta_vira_a_semana and intervalos_que_nao_viram_a_semana.filter(
            Q(data_hora_inicio__lte=data_hora_inicio) &
            Q(data_hora_fim__gte=data_hora_fim)
        ).exists():
            return True

        if not consulta_vira_a_semana and intervalo_que_vira_a_semana.filter(
            Q(data_hora_inicio__lte=data_hora_inicio) |
            Q(data_hora_fim__gte=data_hora_fim)
        ).exists():
            return True

        if consulta_vira_a_semana and intervalo_que_vira_a_semana.filter(
            Q(data_hora_inicio__lte=data_hora_inicio) &
            Q(data_hora_fim__gte=data_hora_fim)
        ).exists():
            return True

        return False
