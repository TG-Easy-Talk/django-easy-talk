import secrets

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import models
from django.db.models import Q, F
from django.urls import reverse
from django.contrib import admin
from django.utils import timezone
from .utilidades.geral import (
    converter_dia_semana_iso_com_hora_para_data_hora,
    desprezar_segundos_e_microssegundos,
    regra_de_3_numero_periodos_por_dia,
)
from .validadores.crp import validate_crp
from .validadores.cpf import validate_cpf
from .validadores.geral import (
    validate_antecedencia,
    validate_valor_consulta,
    validate_intervalo_disponibilidade_data_hora_range,
    validate_usuario_nao_psicologo,
    validate_usuario_nao_paciente,
    validate_divisivel_por_duracao_consulta,
)
from .constantes import (
    CONSULTA_DURACAO,
    CONSULTA_ANTECEDENCIA_MINIMA,
    CONSULTA_ANTECEDENCIA_MAXIMA,
    NUMERO_PERIODOS_POR_DIA,
)
from datetime import UTC, timedelta, time
import json


class BasePacienteOuPsicologo(models.Model):
    def ja_tem_consulta_em(self, data_hora):
        """
        Verifica se já há alguma consulta que tomaria tempo da data-hora enviada.
        """
        return self.consultas.filter(
            Q(data_hora_agendada__gt = data_hora - CONSULTA_DURACAO) &
            Q(data_hora_agendada__lt = data_hora + CONSULTA_DURACAO) &
            ~ Q(estado = EstadoConsulta.CANCELADA)
        ).exists()

    def get_url_foto_propria_ou_padrao(self):
        if self.foto:
            return self.foto.url
        return settings.STATIC_URL + "img/foto_de_perfil.jpg"

    class Meta:
        abstract = True


class Paciente(BasePacienteOuPsicologo):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name="Usuário",
        on_delete=models.CASCADE,
        related_name="paciente",
        validators=[validate_usuario_nao_psicologo],
    )
    nome = models.CharField("Nome", max_length=50)
    cpf = models.CharField("CPF", max_length=14, unique=True, validators=[validate_cpf])
    foto = models.ImageField("Foto", upload_to="pacientes/fotos/", blank=True, null=True)

    class Meta:
        verbose_name = "Paciente"
        verbose_name_plural = "Pacientes"

    def __str__(self):
        return self.nome


class Especializacao(models.Model):
    titulo = models.CharField("Título", max_length=50, unique=True)
    descricao = models.TextField("Descrição")

    class Meta:
        verbose_name = "Especialização"
        verbose_name_plural = "Especializações"

    def __str__(self):
        return self.titulo


class PsicologoCompletosManager(models.Manager):
    def get_filtros(self):
        return (
            Q(valor_consulta__isnull=False) &
            Q(especializacoes__isnull=False) &
            Q(disponibilidade__isnull=False)
        )

    def get_queryset(self):
        return super().get_queryset().filter(self.get_filtros()).distinct()


class Psicologo(BasePacienteOuPsicologo):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name="Usuário",
        on_delete=models.CASCADE,
        related_name="psicologo",
        validators=[validate_usuario_nao_paciente],
    )
    nome_completo = models.CharField("Nome Completo", max_length=50)
    crp = models.CharField("CRP", max_length=20, unique=True, validators=[validate_crp])
    foto = models.ImageField("Foto", upload_to="psicologos/fotos/", blank=True, null=True)
    sobre_mim = models.TextField("Sobre Mim", blank=True, null=True)
    valor_consulta = models.DecimalField(
        "Valor da Consulta",
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[validate_valor_consulta],
        help_text="Entre R$ 20,00 e R$ 4.999,99",
    )
    especializacoes = models.ManyToManyField(
        Especializacao,
        verbose_name="Especializações",
        related_name="psicologos",
        blank=True,
    )

    objects = models.Manager() # Manager padrão (deve ser declarado explicitamente por conta do manager customizado abaixo)
    completos = PsicologoCompletosManager() # Manager para psicólogos com perfil completo

    class Meta:
        verbose_name = "Psicólogo"
        verbose_name_plural = "Psicólogos"

    @property
    def primeiro_nome(self):
        return self.nome_completo.split()[0]

    @property
    @admin.display(boolean=True)
    def esta_com_perfil_completo(self):
        from terapia.services import DisponibilidadeService
        from django.utils import timezone
        
        return bool(
            self.valor_consulta and
            self.especializacoes.exists() and
            DisponibilidadeService.tem_disponibilidade_na_semana(self, timezone.localdate())
        )

    @property
    def intervalo_de_semana_completa(self):
        return self.disponibilidade.filter(data_hora_inicio=F("data_hora_fim"))

    @property
    def intervalos_que_nao_viram_a_semana(self):
        return self.disponibilidade.filter(data_hora_inicio__lt=F("data_hora_fim"))

    @property
    def intervalo_que_vira_a_semana(self):
        return self.disponibilidade.filter(data_hora_fim__lt=F("data_hora_inicio"))

    @property
    def proxima_data_hora_agendavel(self):
        """
        Retorna a data-hora agendável mais próxima do psicólogo.
        """
        from terapia.services import DisponibilidadeService
        
        agora = timezone.now()
        data_limite = agora + CONSULTA_ANTECEDENCIA_MAXIMA
        
        # Iterate week by week
        semana_atual = DisponibilidadeService.obter_semana_inicio(agora)
        semana_limite = DisponibilidadeService.obter_semana_inicio(data_limite)
        
        semana_iter = semana_atual
        while semana_iter <= semana_limite:
            intervalos = DisponibilidadeService.obter_intervalos_para_semana(self, semana_iter)
            
            # Sort intervals by start time
            lista_intervalos = []
            for intervalo in intervalos:
                if isinstance(intervalo, dict):
                    lista_intervalos.append((intervalo['data_hora_inicio'], intervalo['data_hora_fim']))
                else:
                    lista_intervalos.append((intervalo.data_hora_inicio, intervalo.data_hora_fim))
            
            lista_intervalos.sort(key=lambda x: x[0])
            
            for inicio, fim in lista_intervalos:
                # Generate slots
                slot = inicio
                while slot + CONSULTA_DURACAO <= fim:
                    if slot >= agora + CONSULTA_ANTECEDENCIA_MINIMA:
                        if slot > data_limite:
                            return None
                        
                        if not self.ja_tem_consulta_em(slot):
                            return slot
                    
                    slot += CONSULTA_DURACAO
            
            semana_iter += timedelta(weeks=1)
            
        return None

    def __str__(self):
        return self.nome_completo

    def get_absolute_url(self):
        return reverse("perfil", kwargs={"pk": self.pk})

    def _get_datas_hora_dos_intervalos_da_mais_proxima_a_mais_distante_partindo_de(self, instante):
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

        for intervalo in self.disponibilidade.all():
            for data_hora in intervalo.get_datas_hora():
                if data_hora >= instante_convertido + CONSULTA_ANTECEDENCIA_MINIMA:
                    datas_hora_essa_semana.append(data_hora)
                else:
                    datas_hora_proxima_semana.append(data_hora)

        datas_hora_ordenadas = sorted(datas_hora_essa_semana) + sorted(datas_hora_proxima_semana)
        return datas_hora_ordenadas

    def _tem_intervalo_onde_cabe_uma_consulta_em(self, data_hora):
        """
        Verifica se o psicólogo tem um intervalo de disponibilidade no qual se
        encaixa uma consulta que começa na data-hora enviada.

        A consulta deve caber completamente no intervalo para que ele seja válido.

        @param data_hora: Data-hora em que a consulta começa.
        @return: True se a consulta se encaixa no intervalo, False caso contrário.
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

        if self.intervalo_de_semana_completa.exists():
            return True

        if data_hora_inicio == data_hora_fim:
            return False

        # Convert availability intervals to UTC for comparison
        intervalos_nao_viram = self.intervalos_que_nao_viram_a_semana.all()
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

        intervalos_viram = self.intervalo_que_vira_a_semana.all()
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

    def get_intervalos_sobrepostos(self, intervalo):
        """
        Verifica se o psicólogo tem um intervalo de disponibilidade que sobrepõe
        o intervalo enviado como parâmetro.

        Se houver qualquer sobreposição, mesmo que parcial, com extremidades inclusas,
        retorna True.
        """
        intervalos_que_nao_viram_a_semana, intervalo_que_vira_a_semana, intervalo_de_semana_completa = [
            qs.exclude(pk=intervalo.pk) for qs in [
                self.intervalos_que_nao_viram_a_semana,
                self.intervalo_que_vira_a_semana,
                self.intervalo_de_semana_completa,
            ]
        ]

        if intervalo_de_semana_completa.exists():
            return intervalo_de_semana_completa

        if intervalo.data_hora_inicio == intervalo.data_hora_fim and self.disponibilidade.exists():
            return self.disponibilidade.all()

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

    def esta_agendavel_em(self, data_hora):
        """
        Verifica se o psicólogo tem disponibilidade para uma consulta que começa na
        data-hora enviada.

        @param data_hora: Data-hora em que a consulta começa.
        @return: True se o psicólogo tem disponibilidade, False caso contrário.
        """
        from terapia.services import DisponibilidadeService
        
        agora = timezone.now()
        
        # Basic validation
        if data_hora < agora + CONSULTA_ANTECEDENCIA_MINIMA:
            return False
            
        if data_hora > agora + CONSULTA_ANTECEDENCIA_MAXIMA:
            return False
            
        if self.ja_tem_consulta_em(data_hora):
            return False
            
        # Check availability intervals for that specific week
        # Use UTC to ensure consistency with template definition
        data_hora_utc = data_hora.astimezone(UTC)
        intervalos = DisponibilidadeService.obter_intervalos_para_semana(self, data_hora_utc)
        
        data_hora_fim_consulta = data_hora + CONSULTA_DURACAO
        
        for intervalo in intervalos:
            # Handle both template dicts and override objects
            if isinstance(intervalo, dict):
                inicio = intervalo['data_hora_inicio']
                fim = intervalo['data_hora_fim']
            else:
                inicio = intervalo.data_hora_inicio
                fim = intervalo.data_hora_fim
                
            # Check if consultation fits in interval
            if inicio <= data_hora and fim >= data_hora_fim_consulta:
                return True
                
        return False

    def get_matriz_disponibilidade_booleanos_em_json(self, semana_referencia=None):
        """
        Cria uma matriz de booleanos que representa a disponibilidade do psicólogo.
        A ideia é que a matriz seja interpretável nos templates, então
        ela é retornada como uma string de JSON que pode ser decodificada
        pelo JavaScript no template.
        """
        from terapia.services import DisponibilidadeService
        
        if semana_referencia is None:
            semana_referencia = timezone.localdate()
            
        def domingo_a_sabado(matriz_disponibilidade_booleanos):
            matriz_disponibilidade_booleanos.insert(0, matriz_disponibilidade_booleanos.pop())

        matriz = [[False] * NUMERO_PERIODOS_POR_DIA for _ in range(7)]
        
        intervalos = DisponibilidadeService.obter_intervalos_para_semana(self, semana_referencia)

        if intervalos:
            for intervalo in intervalos:
                # Handle both template dicts and override objects
                if isinstance(intervalo, dict):
                    # Template dict already has timezone aware datetimes
                    data_hora_inicio = intervalo['data_hora_inicio']
                    data_hora_fim = intervalo['data_hora_fim']
                else:
                    data_hora_inicio = intervalo.data_hora_inicio
                    data_hora_fim = intervalo.data_hora_fim
                
                # Convert to local time
                data_hora_inicio = timezone.localtime(data_hora_inicio)
                data_hora_fim = timezone.localtime(data_hora_fim)
                
                dia_semana_inicio = data_hora_inicio.isoweekday() - 1
                dia_semana_fim = data_hora_fim.isoweekday() - 1
                
                hil = data_hora_inicio.time()
                hfl = data_hora_fim.time()
                
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


class IntervaloDisponibilidadeManager(models.Manager):
    def inicializar_por_dia_semana_e_hora(self,
        dia_semana_inicio_iso,
        hora_inicio,
        dia_semana_fim_iso,
        hora_fim,
        fuso,
        psicologo=None,
    ):
        intervalo = self.model(
            data_hora_inicio=converter_dia_semana_iso_com_hora_para_data_hora(dia_semana_inicio_iso, hora_inicio, fuso),
            data_hora_fim=converter_dia_semana_iso_com_hora_para_data_hora(dia_semana_fim_iso, hora_fim, fuso),
            psicologo=psicologo,
        )
        return intervalo

    def criar_por_dia_semana_e_hora(self,
        dia_semana_inicio_iso,
        hora_inicio,
        dia_semana_fim_iso,
        hora_fim,
        fuso,
        psicologo,
    ):
        intervalo = self.inicializar_por_dia_semana_e_hora(
            dia_semana_inicio_iso=dia_semana_inicio_iso,
            hora_inicio=hora_inicio,
            dia_semana_fim_iso=dia_semana_fim_iso,
            hora_fim=hora_fim,
            fuso=fuso,
            psicologo=psicologo,
        )
        intervalo.save()
        return intervalo

INTERVALO_DISPONIBILIDADE_DATA_HORA_HELP_TEXT = (
    "A data deste campo é apenas utilizada para obter o dia da semana do intervalo,"
    " o que significa que a data em si não importa desde que o dia da semana esteja correto."
    " Por conveniência, usa-se a semana de 01/07/2024 até 07/07/2024, isto é,"
    " datetime(2024, 7, 1, 0, 0) até datetime(2024, 7, 7, 23, 59). A razão para isso é que nessa semana,"
    " o número do dia do mês é o mesmo do dia da semana no formato ISO, ou seja:"
    " 01/07/2024 é segunda (1),"
    " 02/07/2024 é terça (2) ..."
    " e 07/07/2024 é domingo (7)."
)


class IntervaloDisponibilidadeManager(models.Manager):
    def inicializar_por_dia_semana_e_hora(self,
        dia_semana_inicio_iso,
        hora_inicio,
        dia_semana_fim_iso,
        hora_fim,
        fuso,
        psicologo=None,
    ):
        intervalo = self.model(
            data_hora_inicio=converter_dia_semana_iso_com_hora_para_data_hora(dia_semana_inicio_iso, hora_inicio, fuso),
            data_hora_fim=converter_dia_semana_iso_com_hora_para_data_hora(dia_semana_fim_iso, hora_fim, fuso),
            psicologo=psicologo,
        )
        return intervalo

    def criar_por_dia_semana_e_hora(self,
        dia_semana_inicio_iso,
        hora_inicio,
        dia_semana_fim_iso,
        hora_fim,
        fuso,
        psicologo,
    ):
        intervalo = self.inicializar_por_dia_semana_e_hora(
            dia_semana_inicio_iso=dia_semana_inicio_iso,
            hora_inicio=hora_inicio,
            dia_semana_fim_iso=dia_semana_fim_iso,
            hora_fim=hora_fim,
            fuso=fuso,
            psicologo=psicologo,
        )
        intervalo.save()
        return intervalo


INTERVALO_DISPONIBILIDADE_DATA_HORA_VALIDADORES = [
    validate_intervalo_disponibilidade_data_hora_range,
    validate_divisivel_por_duracao_consulta,
]

class IntervaloDisponibilidade(models.Model):
    data_hora_inicio = models.DateTimeField(
        "Dia da semana e hora do início do intervalo",
        help_text=INTERVALO_DISPONIBILIDADE_DATA_HORA_HELP_TEXT,
        validators=INTERVALO_DISPONIBILIDADE_DATA_HORA_VALIDADORES,
    )
    data_hora_fim = models.DateTimeField(
        "Dia da semana e hora do fim do intervalo",
        help_text=INTERVALO_DISPONIBILIDADE_DATA_HORA_HELP_TEXT,
        validators=INTERVALO_DISPONIBILIDADE_DATA_HORA_VALIDADORES,
    )
    psicologo = models.ForeignKey(
        Psicologo,
        verbose_name="Psicólogo",
        on_delete=models.CASCADE,
        related_name="disponibilidade",
    )
    objects = IntervaloDisponibilidadeManager()

    @property
    def data_hora_inicio_local(self):
        return timezone.localtime(self.data_hora_inicio)

    @property
    def data_hora_fim_local(self):
        return timezone.localtime(self.data_hora_fim)

    @property
    def dia_semana_inicio_local(self):
        return self.data_hora_inicio_local.isoweekday()

    @property
    def dia_semana_fim_local(self):
        return self.data_hora_fim_local.isoweekday()

    @property
    def hora_inicio_local(self):
        return self.data_hora_inicio_local.time()

    @property
    def hora_fim_local(self):
        return self.data_hora_fim_local.time()

    dias_semana_iso = {
        1: "Segunda",
        2: "Terça",
        3: "Quarta",
        4: "Quinta",
        5: "Sexta",
        6: "Sábado",
        7: "Domingo",
    }

    @property
    def nome_dia_semana_inicio_local(self):
        return self.dias_semana_iso[self.dia_semana_inicio_local]

    @property
    def nome_dia_semana_fim_local(self):
        return self.dias_semana_iso[self.dia_semana_fim_local]

    @property
    def duracao(self):
        duracao = self.data_hora_fim - self.data_hora_inicio

        if self.vira_a_semana():
            duracao += timedelta(weeks=1)

        return duracao

    class Meta:
        verbose_name = "Intervalo de Disponibilidade"
        verbose_name_plural = "Intervalos de Disponibilidade"
        ordering = ["data_hora_inicio"]

    def descrever(self, fuso=UTC):
        with timezone.override(fuso):
            return f"{self.nome_dia_semana_inicio_local} às {self.hora_inicio_local} até {self.nome_dia_semana_fim_local} às {self.hora_fim_local} ({fuso})"

    def __str__(self):
        return self.descrever(timezone.get_current_timezone())

    def vira_a_semana(self):
        """
        Verifica se o intervalo começa em uma semana e termina em outra.
        """
        return self.data_hora_fim <= self.data_hora_inicio

    def dura_uma_semana_completa(self):
        """
        Verifica se o intervalo dura exatamente uma semana completa.
        """
        return self.data_hora_inicio == self.data_hora_fim

    def __contains__(self, data_hora):
        """
        Verifica se a data (considera-se apenas o dia da semana) e hora estão contidas no intervalo.

        @param data_hora: A data-hora (a data em si será desprezada, considerando-se apenas o dia da semana)
        @return: True se estiver contido, False caso contrário.
        """
        if self.data_hora_inicio < self.data_hora_fim:
            return self.data_hora_inicio <= data_hora <= self.data_hora_fim

        return not (self.data_hora_fim < data_hora < self.data_hora_inicio)

    def tem_as_mesmas_datas_hora_que(self, outro_intervalo):
        if self.dura_uma_semana_completa():
            return outro_intervalo.dura_uma_semana_completa()

        # Compare using weekday and time components only (timezone-agnostic)
        self_inicio_utc = timezone.localtime(self.data_hora_inicio, UTC)
        self_fim_utc = timezone.localtime(self.data_hora_fim, UTC)
        outro_inicio_utc = timezone.localtime(outro_intervalo.data_hora_inicio, UTC)
        outro_fim_utc = timezone.localtime(outro_intervalo.data_hora_fim, UTC)

        return (
                self_inicio_utc.isoweekday() == outro_inicio_utc.isoweekday() and
                self_inicio_utc.hour == outro_inicio_utc.hour and
                self_inicio_utc.minute == outro_inicio_utc.minute and
                self_fim_utc.isoweekday() == outro_fim_utc.isoweekday() and
                self_fim_utc.hour == outro_fim_utc.hour and
                self_fim_utc.minute == outro_fim_utc.minute
        )

    def get_datas_hora(self):
        """
        Retorna a lista de datas e horas que estão dentro do intervalo,
        dando passos correspondentes à duração de uma consulta.
        """
        datas_hora = []
        data_hora_atual = self.data_hora_inicio
        virou_a_semana = False

        while True:
            datas_hora.append(data_hora_atual)
            data_hora_atual = data_hora_atual + CONSULTA_DURACAO

            if data_hora_atual > converter_dia_semana_iso_com_hora_para_data_hora(7, time(23, 59), data_hora_atual.tzinfo):
                data_hora_atual -= timedelta(weeks=1)
                virou_a_semana = True

            if (
                (self.data_hora_inicio < self.data_hora_fim or virou_a_semana) and
                data_hora_atual > self.data_hora_fim - CONSULTA_DURACAO
            ):
                break

        return datas_hora

    def clean(self):
        super().clean()

        if self.data_hora_inicio is not None and self.data_hora_fim is not None:
            self.data_hora_inicio = desprezar_segundos_e_microssegundos(self.data_hora_inicio)
            self.data_hora_fim = desprezar_segundos_e_microssegundos(self.data_hora_fim)

            if hasattr(self, "psicologo") and self.psicologo:
                if intervalos_sobrepostos := self.psicologo.get_intervalos_sobrepostos(self):
                    intervalos_str = ""
                    quantidade_intervalos = intervalos_sobrepostos.count()
                    plural = quantidade_intervalos > 1
                    plural_s = "s" if plural else ""
                    plural_m = "m" if plural else ""

                    for i, intervalo in enumerate(intervalos_sobrepostos.iterator()):
                        intervalos_str += f"{str(intervalo)}"

                        if i < quantidade_intervalos - 2:
                            intervalos_str += ", "
                        elif i == quantidade_intervalos - 2:
                            intervalos_str += " e "

                    raise ValidationError(
                        f"Este intervalo sobrepõe outro{plural_s} intervalo{plural_s} que já existe{plural_m}: %(intervalos)s",
                        params={"intervalos": intervalos_str},
                        code="sobreposicao_intervalos",
                    )

    @staticmethod
    def from_matriz(matriz_disponibilidade_booleanos):
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


class EstadoConsulta(models.TextChoices):
    SOLICITADA = "SOLICITADA", "Solicitada"
    CONFIRMADA = "CONFIRMADA", "Confirmada"
    CANCELADA = "CANCELADA", "Cancelada"
    EM_ANDAMENTO = "EM_ANDAMENTO", "Em andamento"
    FINALIZADA = "FINALIZADA", "Finalizada"
    __empty__ = "Estado"


class Consulta(models.Model):
    data_hora_solicitada = models.DateTimeField(auto_now_add=True)
    data_hora_agendada = models.DateTimeField(
        "Data-hora agendada para a consulta",
        validators=[validate_antecedencia, validate_divisivel_por_duracao_consulta],
    )
    duracao = models.DurationField(
        "Duração que a consulta teve em minutos",
        blank=True,
        null=True,
    )
    estado = models.CharField(
        "Estado",
        max_length=20,
        choices=EstadoConsulta.choices,
        default=EstadoConsulta.SOLICITADA,
    )
    anotacoes = models.TextField("Anotações", blank=True, null=True)
    checklist_tarefas = models.TextField("Checklist de tarefas", blank=True, null=True)
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='consultas')
    psicologo = models.ForeignKey(
        Psicologo,
        on_delete=models.CASCADE,
        related_name="consultas",
        limit_choices_to=Psicologo.completos.get_filtros(),
    )
    jitsi_room = models.CharField(
        "Sala Jitsi",
        max_length=128,
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = "Consulta"
        verbose_name_plural = "Consultas"
        ordering = ["-data_hora_solicitada", "-data_hora_agendada"]
        indexes = [
            # Filtragens por estado + janela de tempo (cron, dashboards)
            models.Index(
                fields=['estado', 'data_hora_agendada'],
                name='consulta_estado_dh_idx',
            ),
            # Conflitos de agenda e listagens por paciente em função do horário
            models.Index(
                fields=['paciente', 'data_hora_agendada'],
                name='consulta_paciente_dh_idx',
            ),
            # Conflitos de agenda e listagens por psicólogo em função do horário
            models.Index(
                fields=['psicologo', 'data_hora_agendada'],
                name='consulta_psicologo_dh_idx',
            ),
        ]

    def clean(self):
        super().clean()
        self.data_hora_agendada = desprezar_segundos_e_microssegundos(self.data_hora_agendada)

        # Validar se o psicólogo está disponível no horário
        if self.psicologo and self.data_hora_agendada:
            if not self.psicologo.esta_agendavel_em(self.data_hora_agendada):
                raise ValidationError({
                    'data_hora_agendada': ValidationError(
                        'O psicólogo não está disponível neste horário.',
                        code='psicologo_nao_disponivel'
                    )
                })

        # Validar se o paciente está disponível no horário (não tem outra consulta)
        if self.paciente and self.data_hora_agendada:
            consultas_conflitantes = Consulta.objects.filter(
                paciente=self.paciente,
                data_hora_agendada=self.data_hora_agendada
            ).exclude(
                estado__in=[EstadoConsulta.CANCELADA, EstadoConsulta.FINALIZADA]
            )

            # Excluir a própria consulta se estiver editando
            if self.pk:
                consultas_conflitantes = consultas_conflitantes.exclude(pk=self.pk)

            if consultas_conflitantes.exists():
                raise ValidationError({
                    'data_hora_agendada': ValidationError(
                        'O paciente já tem uma consulta agendada neste horário.',
                        code='paciente_nao_disponivel'
                    )
                })

    def atualizar_estado_automatico(self, agora=None):
        """
        Atualiza o estado da consulta com base em 'data_hora_agendada'
        e na duração padrão da consulta (CONSULTA_DURACAO).

        Regras:
        - Antes do horário de início: não altera nada.
        - Entre início e fim:
            * SOLICITADA  -> CANCELADA (psicólogo não respondeu a tempo)
            * CONFIRMADA  -> EM_ANDAMENTO (consulta começou)
        - Após o fim:
            * SOLICITADA  -> CANCELADA
            * CONFIRMADA  -> FINALIZADA
            * EM_ANDAMENTO -> FINALIZADA
        - CANCELADA e FINALIZADA permanecem inalteradas.
        """
        if agora is None:
            agora = timezone.now()

        if self.estado in (EstadoConsulta.CANCELADA, EstadoConsulta.FINALIZADA):
            return False

        inicio = self.data_hora_agendada
        fim = self.data_hora_agendada + CONSULTA_DURACAO
        novo_estado = self.estado

        if inicio <= agora < fim:
            if self.estado == EstadoConsulta.SOLICITADA:
                novo_estado = EstadoConsulta.CANCELADA
                for destinatario in (self.paciente.usuario, self.psicologo.usuario):
                    Notificacao.objects.create(
                        tipo=TipoNotificacao.CONSULTA_EXPIRADA,
                        destinatario=destinatario,
                        consulta=self,
                    )

            elif self.estado == EstadoConsulta.CONFIRMADA:
                novo_estado = EstadoConsulta.EM_ANDAMENTO
                for destinatario in (self.paciente.usuario, self.psicologo.usuario):
                    Notificacao.objects.create(
                        tipo=TipoNotificacao.CONSULTA_EM_ANDAMENTO,
                        destinatario=destinatario,
                        consulta=self,
                    )

        elif agora >= fim:
            if self.estado == EstadoConsulta.SOLICITADA:
                novo_estado = EstadoConsulta.CANCELADA
                for destinatario in (self.paciente.usuario, self.psicologo.usuario):
                    Notificacao.objects.create(
                        tipo=TipoNotificacao.CONSULTA_EXPIRADA,
                        destinatario=destinatario,
                        consulta=self,
                    )

            elif self.estado in (EstadoConsulta.CONFIRMADA, EstadoConsulta.EM_ANDAMENTO):
                novo_estado = EstadoConsulta.FINALIZADA

        if novo_estado != self.estado:
            self.estado = novo_estado
            self.save(update_fields=["estado"])
            return True

        return False

    @classmethod
    def atualizar_estados_automaticamente(cls, queryset=None):
        """
        Atualiza automaticamente o estado de todas as consultas do queryset.
        Se nenhum queryset for informado, atualiza todas as consultas.
        """
        if queryset is None:
            queryset = cls.objects.all()

        agora = timezone.now()
        for consulta in queryset:
            consulta.atualizar_estado_automatico(agora=agora)

    def ensure_jitsi_room(self):
        """
        Gera um identificador de sala Jitsi *curto* se ainda não existir.
        Ex: 'cnslt-a1b2c3'
        """
        if not self.jitsi_room:
            token = secrets.token_urlsafe(6)
            self.jitsi_room = f"cnslt-{token}"
            self.save(update_fields=["jitsi_room"])
        return self.jitsi_room

    @property
    def jitsi_join_url(self):
        """
        URL completa para abrir a call direto no meet.jit.si.
        Ex: https://meet.jit.si/cnslt-a1b2c3
        """
        if not self.jitsi_room:
            self.ensure_jitsi_room()
        return f"https://meet.jit.si/{self.jitsi_room}"

    def __str__(self):
        return (
            f"Consulta {self.estado.upper()} agendada para "
            f"{timezone.localtime(self.data_hora_agendada):%d/%m/%Y %H:%M} "
            f"({timezone.get_current_timezone_name()}) com "
            f"{self.paciente.nome} e {self.psicologo.nome_completo}"
        )


class TipoNotificacao(models.TextChoices):
    CONSULTA_SOLICITADA = "CONSULTA_SOLICITADA", "Consulta Solicitada"
    CONSULTA_CONFIRMADA = "CONSULTA_CONFIRMADA", "Consulta Confirmada"
    CONSULTA_CANCELADA = "CONSULTA_CANCELADA", "Consulta Cancelada"
    CONSULTA_RECUSADA = "CONSULTA_RECUSADA", "Consulta Recusada"
    CONSULTA_EM_ANDAMENTO = "CONSULTA_EM_ANDAMENTO", "Consulta Em Andamento"
    CONSULTA_EXPIRADA = "CONSULTA_EXPIRADA", "Consulta Expirada"

class Notificacao(models.Model):
    tipo = models.CharField("Tipo", max_length=50, choices=TipoNotificacao.choices)
    lida = models.BooleanField("Lida", default=False)
    data_hora_criada = models.DateTimeField(auto_now_add=True)
    remetente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Remetente",
        on_delete=models.CASCADE,
        related_name="notificacoes_como_remetente",
        blank=True,
        null=True,
    )
    destinatario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Destinatário",
        on_delete=models.CASCADE,
        related_name="notificacoes_como_destinatario",
    )
    consulta = models.ForeignKey(
        Consulta,
        verbose_name="Consulta",
        on_delete=models.CASCADE,
        related_name="notificacoes",
    )

    @property
    def mensagem(self):
        mensagens = {
            TipoNotificacao.CONSULTA_SOLICITADA: "O paciente {remetente} solicitou uma nova consulta agendada para {data_hora_agendada}.",
            TipoNotificacao.CONSULTA_CONFIRMADA: "O psicólogo {remetente} aceitou sua solicitação de consulta agendada para {data_hora_agendada}.",
            TipoNotificacao.CONSULTA_RECUSADA: "O psicólogo {remetente} recusou sua solicitação de consulta agendada para {data_hora_agendada}.",
            TipoNotificacao.CONSULTA_CANCELADA: "O paciente {remetente} cancelou a consulta agendada para {data_hora_agendada}.",
            TipoNotificacao.CONSULTA_EM_ANDAMENTO: 'Você tem uma consulta em andamento. Acesse "Minhas Consultas" para ingressar na chamada.',
            TipoNotificacao.CONSULTA_EXPIRADA: "A solicitação de consulta agendada para {data_hora_agendada} expirou por não ter sido respondida.",
        }

        if self.tipo == TipoNotificacao.CONSULTA_EM_ANDAMENTO:
            return mensagens[self.tipo]
        elif self.tipo == TipoNotificacao.CONSULTA_EXPIRADA:
            return mensagens[self.tipo].format(
                data_hora_agendada=timezone.localtime(self.consulta.data_hora_agendada).strftime("%d/%m/%Y %H:%M"),
            )
        return mensagens[self.tipo].format(
            remetente=self.remetente.paciente.nome if self.remetente.is_paciente else self.remetente.psicologo.nome_completo,
            data_hora_agendada=timezone.localtime(self.consulta.data_hora_agendada).strftime("%d/%m/%Y %H:%M"),
        )

    class Meta:
        verbose_name = "Notificação"
        verbose_name_plural = "Notificações"
        ordering = ["-data_hora_criada"]

    def __str__(self):
        return f"Notificação de {self.tipo} de {self.remetente} para {self.destinatario}"

    def save(self, *args, **kwargs):
        if self._state.adding:
            send_mail(
                subject=self.get_tipo_display(),
                message=self.mensagem,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[self.destinatario.email],
            )

        super().save(*args, **kwargs)


# ============================================================================
# New Models for Weekly Availability Granularity (Hybrid Architecture)
# ============================================================================

class IntervaloDisponibilidadeTemplate(models.Model):
    """
    Template de disponibilidade recorrente semanal.
    Define o horário "padrão" do psicólogo que se repete toda semana.
    
    Este modelo não armazena datas específicas, apenas dias da semana (1-7) e horários.
    Quando consultado, o sistema converte este template para datas reais conforme necessário.
    """
    dia_semana_inicio_iso = models.IntegerField(
        "Dia da semana de início",
        help_text="1=Segunda, 2=Terça, ..., 7=Domingo (formato ISO)",
    )
    hora_inicio = models.TimeField("Hora de início")
    dia_semana_fim_iso = models.IntegerField(
        "Dia da semana de fim",
        help_text="1=Segunda, 2=Terça, ..., 7=Domingo (formato ISO)",
    )
    hora_fim = models.TimeField("Hora de fim")
    psicologo = models.ForeignKey(
        Psicologo,
        verbose_name="Psicólogo",
        on_delete=models.CASCADE,
        related_name="disponibilidade_template"
    )
    
    class Meta:
        verbose_name = "Template de Disponibilidade"
        verbose_name_plural = "Templates de Disponibilidade"
        ordering = ["dia_semana_inicio_iso", "hora_inicio"]
    
    def __str__(self):
        dias = {1: "Seg", 2: "Ter", 3: "Qua", 4: "Qui", 5: "Sex", 6: "Sáb", 7: "Dom"}
        return f"{dias.get(self.dia_semana_inicio_iso)} {self.hora_inicio.strftime('%H:%M')} - {dias.get(self.dia_semana_fim_iso)} {self.hora_fim.strftime('%H:%M')}"
    
    @property
    def vira_a_semana(self):
        """Verifica se o intervalo começa em uma semana e termina em outra."""
        if self.dia_semana_inicio_iso == self.dia_semana_fim_iso:
            return self.hora_fim <= self.hora_inicio
        return self.dia_semana_fim_iso < self.dia_semana_inicio_iso
    
    def clean(self):
        super().clean()
        
        # Validate day of week range
        if not (1 <= self.dia_semana_inicio_iso <= 7):
            raise ValidationError("Dia da semana de início deve estar entre 1 (Segunda) e 7 (Domingo)")
        if not (1 <= self.dia_semana_fim_iso <= 7):
            raise ValidationError("Dia da semana de fim deve estar entre 1 (Segunda) e 7 (Domingo)")


class IntervaloDisponibilidadeOverride(models.Model):
    """
    Override de disponibilidade para uma semana específica.
    Permite adicionar horários extras ou substituir completamente o template para uma semana.
    
    Este modelo armazena datas reais (não apenas dias da semana).
    """
    semana_inicio = models.DateField(
        "Segunda-feira da semana",
        help_text="Sempre armazenar a segunda-feira da semana (isoweekday=1)",
        db_index=True,
    )
    data_hora_inicio = models.DateTimeField("Data e hora de início")
    data_hora_fim = models.DateTimeField("Data e hora de fim")
    psicologo = models.ForeignKey(
        Psicologo,
        verbose_name="Psicólogo",
        on_delete=models.CASCADE,
        related_name="disponibilidade_overrides"
    )
    
    class Meta:
        verbose_name = "Override de Disponibilidade"
        verbose_name_plural = "Overrides de Disponibilidade"
        ordering = ["semana_inicio", "data_hora_inicio"]
        indexes = [
            models.Index(fields=['psicologo', 'semana_inicio']),
            models.Index(fields=['data_hora_inicio', 'data_hora_fim']),
        ]
        unique_together = [['psicologo', 'semana_inicio', 'data_hora_inicio']]
    
    def __str__(self):
        return f"{self.psicologo.primeiro_nome} - Semana {self.semana_inicio.strftime('%d/%m/%Y')}: {self.data_hora_inicio.strftime('%d/%m %H:%M')} - {self.data_hora_fim.strftime('%d/%m %H:%M')}"
    
    def clean(self):
        super().clean()
        
        # Ensure semana_inicio is always a Monday
        if self.semana_inicio and self.semana_inicio.weekday() != 0:
            raise ValidationError("semana_inicio deve ser sempre uma segunda-feira")


class SemanaDisponibilidadeConfig(models.Model):
    """
    Configuração de como uma semana específica deve se comportar.
    
    - TEMPLATE: Usa o template padrão do psicólogo (comportamento default)
    - CUSTOM: Usa apenas overrides, ignora o template
    - UNAVAILABLE: Psicólogo indisponível nesta semana (sem atendimentos)
    """
    COMPORTAMENTO_CHOICES = [
        ('TEMPLATE', 'Usar template padrão'),
        ('CUSTOM', 'Horários customizados (ignorar template)'),
        ('UNAVAILABLE', 'Indisponível (sem atendimentos)'),
    ]
    
    psicologo = models.ForeignKey(
        Psicologo,
        verbose_name="Psicólogo",
        on_delete=models.CASCADE,
        related_name="config_semanas"
    )
    semana_inicio = models.DateField(
        "Segunda-feira da semana",
        help_text="Sempre armazenar a segunda-feira da semana (isoweekday=1)",
        db_index=True,
    )
    comportamento = models.CharField(
        "Comportamento",
        max_length=20,
        choices=COMPORTAMENTO_CHOICES,
        default='TEMPLATE'
    )
    
    class Meta:
        verbose_name = "Configuração de Semana"
        verbose_name_plural = "Configurações de Semanas"
        unique_together = [['psicologo', 'semana_inicio']]
        ordering = ["semana_inicio"]
    
    def __str__(self):
        return f"{self.psicologo.primeiro_nome} - Semana {self.semana_inicio.strftime('%d/%m/%Y')}: {self.get_comportamento_display()}"
    
    def clean(self):
        super().clean()
        
        # Ensure semana_inicio is always a Monday
        if self.semana_inicio and self.semana_inicio.weekday() != 0:
            raise ValidationError("semana_inicio deve ser sempre uma segunda-feira")

