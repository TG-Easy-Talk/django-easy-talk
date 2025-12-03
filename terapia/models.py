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
        return bool(
            self.valor_consulta and
            self.especializacoes.exists() and
            self.disponibilidade.exists()
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
        from .service import PsicologoService
        return PsicologoService.obter_proxima_disponibilidade(self)

    def __str__(self):
        return self.nome_completo

    def get_absolute_url(self):
        return reverse("perfil", kwargs={"pk": self.pk})

    def _get_datas_hora_dos_intervalos_da_mais_proxima_a_mais_distante_partindo_de(self, instante):
        """
        Retorna as datas e horas dos intervalos de disponibilidade do psicólogo na ordem do mais
        próximo ao mais distante partindo de um instante no tempo.
        """
        from .service import PsicologoService
        return PsicologoService._get_datas_hora_dos_intervalos_da_mais_proxima_a_mais_distante_partindo_de(self, instante)

    def _tem_intervalo_onde_cabe_uma_consulta_em(self, data_hora):
        """
        Verifica se o psicólogo tem um intervalo de disponibilidade no qual se
        encaixa uma consulta que começa na data-hora enviada.

        A consulta deve caber completamente no intervalo para que ele seja válido.

        @param data_hora: Data-hora em que a consulta começa.
        @return: True se a consulta se encaixa no intervalo, False caso contrário.
        """
        from .service import PsicologoService
        return PsicologoService._tem_intervalo_onde_cabe_uma_consulta_em(self, data_hora)

    def get_intervalos_sobrepostos(self, intervalo):
        """
        Verifica se o psicólogo tem um intervalo de disponibilidade que sobrepõe
        o intervalo enviado como parâmetro.

        Se houver qualquer sobreposição, mesmo que parcial, com extremidades inclusas,
        retorna True.
        """
        from .service import PsicologoService
        return PsicologoService.obter_intervalos_sobrepostos(self, intervalo)

    def esta_agendavel_em(self, data_hora):
        """
        Verifica se o psicólogo tem disponibilidade para uma consulta que começa na
        data-hora enviada.

        @param data_hora: Data-hora em que a consulta começa.
        @return: True se o psicólogo tem disponibilidade, False caso contrário.
        """
        from .service import PsicologoService
        return PsicologoService.verificar_disponibilidade(self, data_hora)

    def get_matriz_disponibilidade_booleanos_em_json(self):
        """
        Cria uma matriz de booleanos que representa a disponibilidade do psicólogo.
        A ideia é que a matriz seja interpretável nos templates, então
        ela é retornada como uma string de JSON que pode ser decodificada
        pelo JavaScript no template.
        """
        from .service import PsicologoService
        return PsicologoService.gerar_matriz_disponibilidade(self)


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
        from .service import PsicologoService
        return PsicologoService.converter_matriz_para_intervalos(matriz_disponibilidade_booleanos)


class EstadoConsulta(models.TextChoices):
    SOLICITADA = "SOLICITADA", "Solicitada"
    CONFIRMADA = "CONFIRMADA", "Confirmada"
    CANCELADA = "CANCELADA", "Cancelada"
    EM_ANDAMENTO = "EM_ANDAMENTO", "Em andamento"
    FINALIZADA = "FINALIZADA", "Finalizada"
    __empty__ = "Estado"


def validate_psicologo_completo(psicologo):
    if isinstance(psicologo, int):
        try:
            psicologo = Psicologo.objects.get(pk=psicologo)
        except Psicologo.DoesNotExist:
            # Se não existe, o ForeignKey padrão já vai reclamar, ou deixamos passar aqui
            return

    if psicologo and not psicologo.esta_com_perfil_completo:
        raise ValidationError(
            'O psicólogo precisa completar o perfil antes de realizar consultas.',
            code='invalid'
        )


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
    checklist_tarefas = models.JSONField("Checklist de tarefas", default=list, blank=True, null=True)
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='consultas')
    psicologo = models.ForeignKey(
        Psicologo,
        on_delete=models.CASCADE,
        related_name="consultas",
        verbose_name="Psicólogo",
        validators=[validate_psicologo_completo],
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
        ordering = ["data_hora_agendada"]

    def clean(self):
        super().clean()
        self.data_hora_agendada = desprezar_segundos_e_microssegundos(self.data_hora_agendada)

        # Validar se o psicólogo está disponível no horário
        if self.psicologo and self.data_hora_agendada:
            validar_disponibilidade = True
            if self.pk:
                original = Consulta.objects.get(pk=self.pk)
                if original.data_hora_agendada == self.data_hora_agendada:
                    validar_disponibilidade = False

            if validar_disponibilidade and not self.psicologo.esta_agendavel_em(self.data_hora_agendada):
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
    
    def save(self, *args, **kwargs):
        pk = self.pk
        consulta = super().save(*args, **kwargs)
        if pk is None:
            Notificacao.objects.create(
                tipo=TipoNotificacao.CONSULTA_SOLICITADA,
                remetente=self.paciente.usuario,
                destinatario=self.psicologo.usuario,
                consulta=self,
            )
        return consulta


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
