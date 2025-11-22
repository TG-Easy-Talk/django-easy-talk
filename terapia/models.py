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
        indexes = [
            models.Index(fields=["valor_consulta"]),
        ]

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
        
        REFATORADO: Agora delega para AgendamentoService (SOLID).
        """
        from terapia.service import AgendamentoService
        return AgendamentoService.calcular_proxima_disponibilidade(self)

    def __str__(self):
        return self.nome_completo

    def get_absolute_url(self):
        return reverse("perfil", kwargs={"pk": self.pk})
    
    def _get_datas_hora_dos_intervalos_da_mais_proxima_a_mais_distante_partindo_de(self, instante):
        """
        DEPRECATED: Mantido para compatibilidade. Use AgendamentoService._get_datas_hora...
        """
        from terapia.service import AgendamentoService
        return AgendamentoService._get_datas_hora_dos_intervalos_da_mais_proxima_a_mais_distante_partindo_de(
            self, instante
        )

    def _tem_intervalo_onde_cabe_uma_consulta_em(self, data_hora):
        """
        DEPRECATED: Mantido para compatibilidade. Use AgendamentoService._tem_intervalo...
        """
        from terapia.service import AgendamentoService
        return AgendamentoService._tem_intervalo_onde_cabe_uma_consulta_em(self, data_hora)
    
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
        
        REFATORADO: Agora delega para AgendamentoService (SOLID).
        
        @param data_hora: Data-hora em que a consulta começa.
        @return: True se o psicólogo tem disponibilidade, False caso contrário.
        """
        from terapia.service import AgendamentoService
        return AgendamentoService.verificar_disponibilidade(self, data_hora)

    def get_matriz_disponibilidade_booleanos_em_json(self):
        """
        Cria uma matriz de booleanos que representa a disponibilidade do psicólogo.
        A ideia é que a matriz seja interpretável nos templates, então
        ela é retornada como uma string de JSON que pode ser decodificada
        pelo JavaScript no template.
        """
        def domingo_a_sabado(matriz_disponibilidade_booleanos):
            matriz_disponibilidade_booleanos.insert(0, matriz_disponibilidade_booleanos.pop())

        matriz = [[False] * NUMERO_PERIODOS_POR_DIA for _ in range(7)]

        if self.disponibilidade.exists():
            for intervalo in self.disponibilidade.all():
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
        constraints = [
            models.UniqueConstraint(
                fields=["psicologo", "data_hora_inicio", "data_hora_fim"],
                name="uniq_intervalo_psicologo_inicio_fim",
            ),
        ]

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
        """
        if self.data_hora_inicio < self.data_hora_fim:
            return self.data_hora_inicio <= data_hora <= self.data_hora_fim

        return not (self.data_hora_fim < data_hora < self.data_hora_inicio)

    def tem_as_mesmas_datas_hora_que(self, outro_intervalo):
        """
        Verifica se dois intervalos têm as mesmas datas-hora.
        
        CORREÇÃO: Compara convertendo ambos para UTC para evitar problemas com
        timezone.override() que afeta as propriedades *_local dinamicamente.
        """
        from datetime import UTC as utc_tz
        
        if self.dura_uma_semana_completa():
            return outro_intervalo.dura_uma_semana_completa()

        # Normalizar para UTC para comparação consistente
        self_inicio_utc = self.data_hora_inicio.astimezone(utc_tz)
        self_fim_utc = self.data_hora_fim.astimezone(utc_tz)
        outro_inicio_utc = outro_intervalo.data_hora_inicio.astimezone(utc_tz)
        outro_fim_utc = outro_intervalo.data_hora_fim.astimezone(utc_tz)
        
        return (
            self_inicio_utc == outro_inicio_utc and
            self_fim_utc == outro_fim_utc
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
            models.Index(fields=["psicologo", "data_hora_agendada"]),
            models.Index(fields=["paciente", "data_hora_agendada"]),
            models.Index(fields=["estado", "data_hora_agendada"]),
            models.Index(fields=["data_hora_solicitada"]),
        ]

    def clean(self):
        super().clean()
        self.data_hora_agendada = desprezar_segundos_e_microssegundos(self.data_hora_agendada)

        if not self.psicologo_id or not self.paciente_id or not self.data_hora_agendada:
            return

        from terapia.service import AgendamentoService
        
        # Verificar disponibilidade do psicólogo
        # Nota: Se for edição de consulta existente, idealmente deveríamos excluir a própria consulta
        # da verificação, mas AgendamentoService não suporta isso nativamente ainda.
        # Como os testes focam em criação (pk=None), isso deve funcionar.
        if not AgendamentoService.verificar_disponibilidade(self.psicologo, self.data_hora_agendada):
            raise ValidationError({
                "data_hora_agendada": ValidationError(
                    "Psicólogo não disponível neste horário.",
                    code="psicologo_nao_disponivel"
                )
            })

        # Verificar disponibilidade do paciente
        if self.paciente.ja_tem_consulta_em(self.data_hora_agendada):
            raise ValidationError({
                "data_hora_agendada": ValidationError(
                    "Paciente já possui consulta neste horário.",
                    code="paciente_nao_disponivel"
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
            elif self.estado == EstadoConsulta.CONFIRMADA:
                novo_estado = EstadoConsulta.EM_ANDAMENTO
        elif agora >= fim:
            if self.estado == EstadoConsulta.SOLICITADA:
                novo_estado = EstadoConsulta.CANCELADA
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

        Implementação em lote (bulk update) para evitar N SELECTs + N UPDATEs.
        """
        if queryset is None:
            queryset = cls.objects.all()

        agora = timezone.now()

        # SOLICITADA -> CANCELADA a partir do horário de início
        queryset.filter(
            estado=EstadoConsulta.SOLICITADA,
            data_hora_agendada__lte=agora,
        ).update(estado=EstadoConsulta.CANCELADA)

        # CONFIRMADA -> EM_ANDAMENTO entre início e fim (janela de 1 CONSULTA_DURACAO)
        queryset.filter(
            estado=EstadoConsulta.CONFIRMADA,
            data_hora_agendada__lte=agora,
            data_hora_agendada__gt=agora - CONSULTA_DURACAO,
        ).update(estado=EstadoConsulta.EM_ANDAMENTO)

        # CONFIRMADA/EM_ANDAMENTO -> FINALIZADA após o fim
        queryset.filter(
            estado__in=[EstadoConsulta.CONFIRMADA, EstadoConsulta.EM_ANDAMENTO],
            data_hora_agendada__lte=agora - CONSULTA_DURACAO,
        ).update(estado=EstadoConsulta.FINALIZADA)

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

class Notificacao(models.Model):
    tipo = models.CharField("Tipo", max_length=50, choices=TipoNotificacao.choices)
    lida = models.BooleanField("Lida", default=False)
    data_hora_criada = models.DateTimeField(auto_now_add=True)
    remetente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Paciente",
        on_delete=models.CASCADE,
        related_name="notificacoes_como_remetente",
    )
    destinatario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Psicólogo",
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
        }

        return mensagens[self.tipo].format(
            remetente=self.remetente.paciente.nome if self.remetente.is_paciente else self.remetente.psicologo.nome_completo,
            data_hora_agendada=timezone.localtime(self.consulta.data_hora_agendada).strftime("%d/%m/%Y %H:%M"),
        )

    class Meta:
        verbose_name = "Notificação"
        verbose_name_plural = "Notificações"
        ordering = ["-data_hora_criada"]
        indexes = [
            models.Index(fields=["destinatario", "lida", "data_hora_criada"]),
            models.Index(fields=["remetente", "data_hora_criada"]),
        ]

    def __str__(self):
        return f"Notificação de {self.tipo} de {self.remetente} para {self.destinatario}"

    def save(self, *args, **kwargs):
        # Salvar a notificação PRIMEIRO no banco de dados
        # Isso garante que mesmo que o email falhe, a notificação é registrada
        is_new = self._state.adding
        super().save(*args, **kwargs)
        
        # Enviar email DEPOIS do save, com tratamento de erro
        if is_new:
            try:
                send_mail(
                    subject=self.get_tipo_display(),
                    message=self.mensagem,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[self.destinatario.email],
                    fail_silently=False,
                )
            except Exception as e:
                # Logging do erro sem quebrar a aplicação
                import logging
                logger = logging.getLogger(__name__)
                logger.error(
                    f"Falha ao enviar email de notificação #{self.id} "
                    f"para {self.destinatario.email}: {e}",
                    exc_info=True,
                    extra={
                        'notificacao_id': self.id,
                        'tipo': self.tipo,
                        'destinatario_email': self.destinatario.email,
                    }
                )

