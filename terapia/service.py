import json
from datetime import UTC, timedelta, time

from django.db import transaction
from django.db.models import Q, F
from django.core.exceptions import ValidationError
from django.utils import timezone

from terapia.models import Consulta, EstadoConsulta, TipoNotificacao, Notificacao, IntervaloDisponibilidade
from terapia.utilidades.geral import (
    converter_dia_semana_iso_com_hora_para_data_hora,
    desprezar_segundos_e_microssegundos,
    regra_de_3_numero_periodos_por_dia,
)
from terapia.constantes import (
    CONSULTA_DURACAO,
    CONSULTA_ANTECEDENCIA_MINIMA,
    CONSULTA_ANTECEDENCIA_MAXIMA,
    NUMERO_PERIODOS_POR_DIA,
)


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
        """
        Retorna a data-hora agendável mais próxima do psicólogo.
        """
        if not psicologo.disponibilidade.exists():
            return None

        semanas = 0
        tempo_decorrido = timedelta(0)
        agora = timezone.localtime()
        agora_convertido = converter_dia_semana_iso_com_hora_para_data_hora(agora.isoweekday(), agora.time(), agora.tzinfo)
        datas_hora_ordenadas = PsicologoService._get_datas_hora_dos_intervalos_da_mais_proxima_a_mais_distante_partindo_de(psicologo, agora)

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
    def verificar_disponibilidade(psicologo, data_hora):
        """
        Verifica se o psicólogo tem disponibilidade para uma consulta que começa na
        data-hora enviada.
        """
        agora = timezone.now()
        proxima_data_hora_agendavel = PsicologoService.obter_proxima_disponibilidade(psicologo)

        return bool(
            psicologo.disponibilidade.exists() and
            proxima_data_hora_agendavel is not None and
            proxima_data_hora_agendavel <= data_hora <= agora + CONSULTA_ANTECEDENCIA_MAXIMA and
            PsicologoService._tem_intervalo_onde_cabe_uma_consulta_em(psicologo, data_hora) and
            not psicologo.ja_tem_consulta_em(data_hora)
        )

    @staticmethod
    def gerar_matriz_disponibilidade(psicologo):
        """
        Cria uma matriz de booleanos que representa a disponibilidade do psicólogo.
        Retorna como uma string de JSON.
        """
        def domingo_a_sabado(matriz_disponibilidade_booleanos):
            matriz_disponibilidade_booleanos.insert(0, matriz_disponibilidade_booleanos.pop())

        matriz = [[False] * NUMERO_PERIODOS_POR_DIA for _ in range(7)]

        if psicologo.disponibilidade.exists():
            for intervalo in psicologo.disponibilidade.all():
                dia_semana_inicio = intervalo.dia_semana_inicio_local - 1
                dia_semana_fim = intervalo.dia_semana_fim_local - 1
                hil = intervalo.hora_inicio_local
                hfl = intervalo.hora_fim_local
                hora_inicio_matriz = regra_de_3_numero_periodos_por_dia(timedelta(hours=hil.hour, minutes=hil.minute).total_seconds() / 3600)
                hora_fim_matriz = regra_de_3_numero_periodos_por_dia(timedelta(hours=hfl.hour, minutes=hfl.minute).total_seconds() / 3600)

                ranges = []

                if dia_semana_inicio == dia_semana_fim and hora_inicio_matriz < hora_fim_matriz:
                    ranges = [range(hora_inicio_matriz, hora_fim_matriz)]
                else:
                    ranges.append(range(hora_inicio_matriz, NUMERO_PERIODOS_POR_DIA))

                    dia_semana_atual = dia_semana_inicio + 1

                    if dia_semana_inicio >= dia_semana_fim:
                        dia_semana_atual -= 7

                    while dia_semana_atual <= dia_semana_fim:
                        if dia_semana_atual != dia_semana_fim:
                            ranges.append(range(0, NUMERO_PERIODOS_POR_DIA))
                        else:
                            ranges.append(range(0, hora_fim_matriz))
                        dia_semana_atual += 1

                for i, _range in enumerate(ranges):
                    for hora in _range:
                        matriz[(dia_semana_inicio + i) % 7][hora] = True

        domingo_a_sabado(matriz)
        matriz_em_json = json.dumps(matriz)
        return matriz_em_json

    @staticmethod
    def converter_matriz_para_intervalos(matriz_disponibilidade_booleanos):
        """
        Converte a matriz de booleanos JSON em objetos de IntervaloDisponibilidade.
        """
        def get_hora_por_indice(indice):
            timedelta_hora = indice * CONSULTA_DURACAO
            return time(timedelta_hora.seconds // 3600, (timedelta_hora.seconds // 60) % 60)

        def segunda_a_domingo(matriz):
            matriz.append(matriz.pop(0))

        def to_dia_semana_iso(indice):
            return indice % 7 + 1

        if isinstance(matriz_disponibilidade_booleanos, (str, bytes, bytearray)):
            m = json.loads(matriz_disponibilidade_booleanos)
        else:
            m = matriz_disponibilidade_booleanos

        if not (isinstance(m,list) and all(isinstance(row, list) for row in m)):
            raise ValueError("Fromato inválido para matriz de disponibilidade")

        segunda_a_domingo(m)

        disponibilidade = []
        intervalo_no_comeco = None

        i = j = 0
        while i < len(m):
            while j < len(m[0]):
                if m[i][j]:
                    comeca_no_inicio_da_semana = i == 0 and j == 0
                    vira_a_semana = False

                    hora_inicio = get_hora_por_indice(j)
                    dia_semana_inicio_iso = to_dia_semana_iso(i)

                    while m[i][j]:
                        if j < len(m[0]) - 1:
                            j += 1
                        else:
                            j = 0
                            i += 1
                            if i >= len(m):
                                vira_a_semana = True
                                break

                    fuso_atual = timezone.get_current_timezone()

                    if vira_a_semana and intervalo_no_comeco:
                        hora_fim = intervalo_no_comeco.hora_fim_local
                        dia_semana_fim_iso = intervalo_no_comeco.dia_semana_fim_local
                        disponibilidade.remove(intervalo_no_comeco)
                    else:
                        hora_fim = get_hora_por_indice(j)
                        dia_semana_fim_iso = to_dia_semana_iso(i)

                    intervalo = IntervaloDisponibilidade.objects.inicializar_por_dia_semana_e_hora(
                        dia_semana_inicio_iso=dia_semana_inicio_iso,
                        hora_inicio=hora_inicio,
                        dia_semana_fim_iso=dia_semana_fim_iso,
                        hora_fim=hora_fim,
                        fuso=fuso_atual,
                    )

                    if comeca_no_inicio_da_semana:
                        intervalo_no_comeco = intervalo

                    disponibilidade.append(intervalo)

                if i >= len(m):
                    break

                j += 1

            j = 0
            i += 1

        return disponibilidade

    @staticmethod
    def _tem_intervalo_onde_cabe_uma_consulta_em(psicologo, data_hora):
        """
        Verifica se o psicólogo tem um intervalo de disponibilidade no qual se
        encaixa uma consulta que começa na data-hora enviada.
        """
        # Normalize to weekday representation in UTC
        data_hora_utc = timezone.localtime(data_hora, UTC)

        data_hora_inicio = converter_dia_semana_iso_com_hora_para_data_hora(
            data_hora_utc.isoweekday(),
            data_hora_utc.time(),
            UTC,
        )

        # Calculate end time
        data_hora_fim_temp = data_hora_utc + CONSULTA_DURACAO
        data_hora_fim = converter_dia_semana_iso_com_hora_para_data_hora(
            data_hora_fim_temp.isoweekday(),
            data_hora_fim_temp.time(),
            UTC,
        )

        consulta_vira_a_semana = data_hora_fim <= data_hora_inicio

        if psicologo.intervalo_de_semana_completa.exists():
            return True

        if data_hora_inicio == data_hora_fim:
            return False

        # Convert availability intervals to UTC for comparison
        intervalos_nao_viram = psicologo.intervalos_que_nao_viram_a_semana.all()
        for intervalo in intervalos_nao_viram:
            intervalo_inicio_utc = timezone.localtime(intervalo.data_hora_inicio, UTC)
            intervalo_fim_utc = timezone.localtime(intervalo.data_hora_fim, UTC)

            intervalo_inicio_normalized = converter_dia_semana_iso_com_hora_para_data_hora(
                intervalo_inicio_utc.isoweekday(),
                intervalo_inicio_utc.time(),
                UTC,
            )
            intervalo_fim_normalized = converter_dia_semana_iso_com_hora_para_data_hora(
                intervalo_fim_utc.isoweekday(),
                intervalo_fim_utc.time(),
                UTC,
            )

            if not consulta_vira_a_semana:
                if intervalo_inicio_normalized <= data_hora_inicio and intervalo_fim_normalized >= data_hora_fim:
                    return True

        intervalos_viram = psicologo.intervalo_que_vira_a_semana.all()
        for intervalo in intervalos_viram:
            intervalo_inicio_utc = timezone.localtime(intervalo.data_hora_inicio, UTC)
            intervalo_fim_utc = timezone.localtime(intervalo.data_hora_fim, UTC)

            intervalo_inicio_normalized = converter_dia_semana_iso_com_hora_para_data_hora(
                intervalo_inicio_utc.isoweekday(),
                intervalo_inicio_utc.time(),
                UTC,
            )
            intervalo_fim_normalized = converter_dia_semana_iso_com_hora_para_data_hora(
                intervalo_fim_utc.isoweekday(),
                intervalo_fim_utc.time(),
                UTC,
            )

            if not consulta_vira_a_semana:
                if intervalo_inicio_normalized <= data_hora_inicio or intervalo_fim_normalized >= data_hora_fim:
                    return True

            if consulta_vira_a_semana:
                if intervalo_inicio_normalized <= data_hora_inicio and intervalo_fim_normalized >= data_hora_fim:
                    return True

        return False

    @staticmethod
    def obter_intervalos_sobrepostos(psicologo, intervalo):
        """
        Verifica se o psicólogo tem um intervalo de disponibilidade que sobrepõe
        o intervalo enviado como parâmetro.
        """
        intervalos_que_nao_viram_a_semana, intervalo_que_vira_a_semana, intervalo_de_semana_completa = [
            qs.exclude(pk=intervalo.pk) for qs in [
                psicologo.intervalos_que_nao_viram_a_semana,
                psicologo.intervalo_que_vira_a_semana,
                psicologo.intervalo_de_semana_completa,
            ]
        ]

        if intervalo_de_semana_completa.exists():
            return intervalo_de_semana_completa

        if intervalo.data_hora_inicio == intervalo.data_hora_fim and psicologo.disponibilidade.exists():
            return psicologo.disponibilidade.all()

        if not intervalo.vira_a_semana() and (qs := intervalos_que_nao_viram_a_semana.filter(
            Q(data_hora_inicio__lte=intervalo.data_hora_fim) &
            Q(data_hora_fim__gte=intervalo.data_hora_inicio)
        )).exists():
            return qs

        if not intervalo.vira_a_semana() and (qs := intervalo_que_vira_a_semana.filter(
            Q(data_hora_inicio__lte=intervalo.data_hora_fim) |
            Q(data_hora_fim__gte=intervalo.data_hora_inicio)
        )).exists():
            return qs

        if intervalo.vira_a_semana() and (qs := intervalo_que_vira_a_semana).exists():
            return qs

        if intervalo.vira_a_semana() and (qs := intervalos_que_nao_viram_a_semana.filter(
            Q(data_hora_inicio__lte=intervalo.data_hora_fim) |
            Q(data_hora_fim__gte=intervalo.data_hora_inicio)
        )).exists():
            return qs

        return None

    @staticmethod
    def _get_datas_hora_dos_intervalos_da_mais_proxima_a_mais_distante_partindo_de(psicologo, instante):
        """
        Retorna as datas e horas dos intervalos de disponibilidade do psicólogo na ordem do mais
        próximo ao mais distante partindo de um instante no tempo.
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
