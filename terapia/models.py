from django.conf import settings
from django.core.exceptions import ValidationError
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
        if not self.disponibilidade.exists():
            return None

        semanas = 0
        tempo_decorrido = timedelta(0)
        agora = timezone.localtime()
        agora_convertido = converter_dia_semana_iso_com_hora_para_data_hora(agora.isoweekday(), agora.time(), agora.tzinfo)
        datas_hora_ordenadas = self._get_datas_hora_dos_intervalos_da_mais_proxima_a_mais_distante_partindo_de(agora)

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
                    not self.ja_tem_consulta_em(data_hora_inicio)
                ):
                    return data_hora_inicio
                
            semanas += 1

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

        if self.intervalo_de_semana_completa.exists():
            return True

        if data_hora_inicio == data_hora_fim:
            return False

        if not consulta_vira_a_semana and self.intervalos_que_nao_viram_a_semana.filter(
            Q(data_hora_inicio__lte=data_hora_inicio) &
            Q(data_hora_fim__gte=data_hora_fim)
        ).exists():
            return True

        if not consulta_vira_a_semana and self.intervalo_que_vira_a_semana.filter(
            Q(data_hora_inicio__lte=data_hora_inicio) |
            Q(data_hora_fim__gte=data_hora_fim)
        ).exists():
            return True

        if consulta_vira_a_semana and self.intervalo_que_vira_a_semana.filter(
            Q(data_hora_inicio__lte=data_hora_inicio) &
            Q(data_hora_fim__gte=data_hora_fim)
        ).exists():
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
        agora = timezone.now()
        proxima_data_hora_agendavel = self.proxima_data_hora_agendavel
        
        return bool(
            self.disponibilidade.exists() and
            proxima_data_hora_agendavel is not None and
            proxima_data_hora_agendavel <= data_hora <= agora + CONSULTA_ANTECEDENCIA_MAXIMA and
            self._tem_intervalo_onde_cabe_uma_consulta_em(data_hora) and
            not self.ja_tem_consulta_em(data_hora)
        )
    
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

        return (
            self.data_hora_inicio == outro_intervalo.data_hora_inicio and
            self.data_hora_fim == outro_intervalo.data_hora_fim
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

    class Meta:
        verbose_name = "Consulta"
        verbose_name_plural = "Consultas"
        ordering = ["-data_hora_solicitada", "-data_hora_agendada"]

    def clean(self):
        super().clean()

        self.data_hora_agendada = desprezar_segundos_e_microssegundos(self.data_hora_agendada)

        criando_um_novo_objeto = self.pk is None

        if criando_um_novo_objeto:
            if hasattr(self, "psicologo") and not self.psicologo.esta_agendavel_em(self.data_hora_agendada):
                raise ValidationError({
                    "data_hora_agendada": ValidationError(
                        "O psicólogo não tem disponibilidade nessa data e horário",
                        code="psicologo_nao_disponivel"
                    )
                })
            
            elif hasattr(self, "paciente") and self.paciente.ja_tem_consulta_em(self.data_hora_agendada):
                raise ValidationError({
                    "data_hora_agendada": ValidationError(
                        "O paciente já tem uma consulta marcada que tomaria o tempo dessa que se deseja agendar",
                        code="paciente_nao_disponivel"
                    )
                })

    def __str__(self):
        return f"Consulta {self.estado.upper()} agendada para {timezone.localtime(self.data_hora_agendada):%d/%m/%Y %H:%M} ({timezone.get_current_timezone_name()}) com {self.paciente.nome} e {self.psicologo.nome_completo}"


class WeekAvailability(models.Model):
    """
    Disponibilidade por semana (granular).
    - week_start: segunda-feira (data) da semana (timezone local do servidor).
    - kind: 'OVERRIDE' (só esta semana) ou 'ANCHOR' (esta e as seguintes, até outra âncora/override).
    - matriz: 7 x NUMERO_PERIODOS_POR_DIA (mesmo formato usado no widget).
    """
    KIND_OVERRIDE = "OVERRIDE"
    KIND_ANCHOR = "ANCHOR"
    KIND_CHOICES = (
        (KIND_OVERRIDE, "Override"),
        (KIND_ANCHOR, "Anchor"),
    )

    psicologo = models.ForeignKey(Psicologo, related_name="week_availability", on_delete=models.CASCADE)
    week_start = models.DateField()  # Monday
    kind = models.CharField(max_length=16, choices=KIND_CHOICES)
    matriz = models.JSONField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["psicologo", "week_start"], name="uniq_psicologo_weekstart")
        ]
        indexes = [
            models.Index(fields=["psicologo", "week_start"]),
            models.Index(fields=["psicologo", "kind", "week_start"]),
        ]
        ordering = ["week_start"]

    def __str__(self):
        return f"{self.psicologo_id} {self.week_start} {self.kind}"
