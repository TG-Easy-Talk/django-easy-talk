from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.contrib import admin
from django.utils import timezone
from .utils.disponibilidade import get_matriz_disponibilidade_booleanos_em_javascript
from .utils.crp import validate_crp
from .utils.cpf import validate_cpf
from .utils.validators import (
    validate_data_hora_agendada,
    validate_valor_consulta,
    validate_intervalo_disponibilidade_datetime_range,
    validate_usuario_nao_psicologo,
    validate_usuario_nao_paciente,
)
from .constants import CONSULTA_DURACAO_MAXIMA
from datetime import datetime, date


class BasePacienteOuPsicologo(models.Model):
    def ja_tem_consulta_em(self, data_hora):
        """
        Verifica se já há alguma consulta que tomaria tempo da data e hora enviadas.
        """
        return self.consultas.filter(
            Q(data_hora_agendada__gt=data_hora - CONSULTA_DURACAO_MAXIMA) &
            Q(data_hora_agendada__lt=data_hora + CONSULTA_DURACAO_MAXIMA) &
            ~ Q(estado=EstadoConsulta.CANCELADA)  # Desconsiderar consultas canceladas
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

    def clean(self):
        super().clean()
        # Caso já exista no banco, checar se já há psicólogo relacionado
        if hasattr(self, "usuario") and self.usuario.is_psicologo:
            raise ValidationError({"usuario": "Este usuário já está relacionado a um psicólogo."})

    def __str__(self):
        return self.nome


class Especializacao(models.Model):
    titulo = models.CharField("Título", max_length=100, unique=True)
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

    objects = models.Manager()  # Manager padrão (deve ser declarado explicitamente por conta do manager customizado abaixo)
    completos = PsicologoCompletosManager()  # Manager para psicólogos com perfil completo

    class Meta:
        verbose_name = "Psicólogo"
        verbose_name_plural = "Psicólogos"

    @property
    def primeiro_nome(self):
        return self.nome_completo.split()[0]

    @property
    @admin.display(boolean=True)
    def esta_com_perfil_completo(self):
        """
        Retorna True se o psicólogo tem perfil completo, ou seja,
        se possui valor de consulta, pelo menos uma especialização e disponibilidade definida.
        """
        return bool(
            self.valor_consulta and
            self.especializacoes.exists() and
            self.disponibilidade.exists()
        )

    @property
    def proxima_data_hora_agendavel(self):
        """
        Retorna a data e hora agendáveis mais próximas do psicólogo.
        """
        if not self.disponibilidade.exists():
            return None

        # i = 0
        # agora = timezone.now()
        # suposta_data_hora_agendavel_mais_proxima = agora + CONSULTA_ANTECEDENCIA_MINIMA

        # if agora.day < suposta_data_hora_agendavel_mais_proxima.day:
        #     i += 1

        # while i < CONSULTA_ANTECEDENCIA_MAXIMA.days:
        #     hoje = agora.date() + timedelta(days=i)
        #     dia_semana = hoje.isoweekday() % 7 + 1  # 1 (domingo) a 7 (sábado)

        #     for intervalo in self._get_intervalos_do_dia_semana(dia_semana):
        #         for hora in get_horas_intervalo(intervalo):
        #             data_hora_inicio = combinar_data_com_str_horario(hoje, f"{hora}:00", agora.tzinfo)

        #             if (
        #                 data_hora_inicio >= suposta_data_hora_agendavel_mais_proxima and
        #                 not self.ja_tem_consulta_em(data_hora_inicio)
        #             ):
        #                 return data_hora_inicio

        #     i += 1

        return None

    def clean(self):
        super().clean()
        # Caso já exista no banco, checar se já há paciente relacionado
        if hasattr(self, "usuario") and self.usuario.is_paciente:
            raise ValidationError({"usuario": "Este usuário já está relacionado a um paciente."})

    def __str__(self):
        return self.nome_completo

    def get_absolute_url(self):
        return reverse("perfil", kwargs={"pk": self.pk})

    def _get_intervalo_em(self, data_hora):
        """
        Retorna, se houver, o intervalo no qual se encaixa uma consulta hipotética
        que começa na data e hora enviadas.
        
        (A consulta deve caber completamente no intervalo para que ele seja retornado).
        
        @param data_hora: Data e hora em que a consulta começa.
        @return: O intervalo no qual a consulta se encaixa ou None caso não exista.
        """
        try:
            return self.disponibilidade.get(
                data_hora_inicio__lte=data_hora,
                data_hora_fim__gte=data_hora + CONSULTA_DURACAO_MAXIMA,
            )
        except IntervaloDisponibilidade.DoesNotExist:
            return None

    def _tem_intervalo_em(self, data_hora):
        """
        Verifica se o psicólogo tem um intervalo de disponibilidade no qual se
        encaixa uma consulta que começa na data e hora enviadas.
        
        (A consulta deve caber completamente no intervalo para que ele seja válido).

        @param data_hora: Data e hora em que a consulta começa.
        @return: True se a consulta se encaixa no intervalo, False caso contrário.
        """
        fuso_atual = timezone.get_current_timezone()
        data_hora_inicio = datetime.combine(date(2024, 7, data_hora.isoweekday()), data_hora.time(), tzinfo=fuso_atual)
        data_hora_final = data_hora_inicio + CONSULTA_DURACAO_MAXIMA
        
        return self.disponibilidade.filter(
            data_hora_inicio__lte=data_hora_inicio,
            data_hora_fim__gte=data_hora_final,
        ).exists()

    def esta_agendavel_em(self, data_hora):
        """
        Verifica se o psicólogo tem disponibilidade para uma consulta que começa na
        data e hora enviadas.
        
        @param data_hora: Data e hora em que a consulta começa.
        @return: True se o psicólogo tem disponibilidade, False caso contrário.
        """
        return bool(
            self.disponibilidade.exists() and
            self._tem_intervalo_em(data_hora) and
            not self.ja_tem_consulta_em(data_hora)
        )

    def get_matriz_disponibilidade_booleanos_em_javascript(self):
        return get_matriz_disponibilidade_booleanos_em_javascript(self.disponibilidade)


INTERVALO_DISPONIBILIDADE_DATA_HORA_HELP_TEXT = (
    "A data deste campo é apenas utilizada para obter o dia da semana do intervalo,"
    " o que significa que a data em si não importa desde que o dia da semana esteja correto."
    " Por conveniência, usa-se a semana de 01/07/2024 até 08/07/2024, isto é,"
    " datetime(2024, 7, 1, 0, 0) até datetime(2024, 7, 8, 0, 0). A razão para isso é que nessa semana,"
    " o número do dia do mês é o mesmo do dia da semana no formato ISO, ou seja:"
    " 01/07/2024 é segunda (1),"
    " 02/07/2024 é terça (2) ..."
    " 07/07/2024 é domingo (7),"
    " e 08/07/2024 é segunda (1) novamente."
)


class IntervaloDisponibilidade(models.Model):
    data_hora_inicio = models.DateTimeField(
        "Dia da semana e hora do início do intervalo",
        help_text=INTERVALO_DISPONIBILIDADE_DATA_HORA_HELP_TEXT,
        validators=[validate_intervalo_disponibilidade_datetime_range],
    )
    data_hora_fim = models.DateTimeField(
        "Dia da semana e hora do fim do intervalo",
        help_text=INTERVALO_DISPONIBILIDADE_DATA_HORA_HELP_TEXT,
        validators=[validate_intervalo_disponibilidade_datetime_range],
    )
    psicologo = models.ForeignKey(
        Psicologo,
        verbose_name="Psicólogo",
        on_delete=models.CASCADE,
        related_name="disponibilidade",
    )

    @property
    def data_hora_inicio_local(self):
        return timezone.localtime(self.data_hora_inicio)
    
    @property
    def data_hora_fim_local(self):
        return timezone.localtime(self.data_hora_fim)

    @property
    def dia_semana_inicio_local(self):
        return self.data_hora_inicio_local.day

    @property
    def dia_semana_fim_local(self):
        return self.data_hora_fim_local.day

    @property
    def hora_inicio_local(self):
        return self.data_hora_inicio_local.time()

    @property
    def hora_fim_local(self):
        return self.data_hora_fim_local.time()

    dias_semana_iso = {
        1: "Segunda (inicial)",
        2: "Terça",
        3: "Quarta",
        4: "Quinta",
        5: "Sexta",
        6: "Sábado",
        7: "Domingo",
        8: "Segunda (final)",  # É usado para quando o intervalo vai até a próxima segunda
    }

    @property
    def nome_dia_semana_inicio_local(self):
        return self.dias_semana_iso[self.dia_semana_inicio_local]

    @property
    def nome_dia_semana_fim_local(self):
        return self.dias_semana_iso[self.dia_semana_fim_local]

    class Meta:
        verbose_name = "Intervalo de Disponibilidade"
        verbose_name_plural = "Intervalos de Disponibilidade"
        ordering = ["data_hora_inicio"]

    def __str__(self):
        return f"{self.nome_dia_semana_inicio_local} às {self.hora_inicio_local} - {self.nome_dia_semana_fim_local} às {self.hora_fim_local}"

    def __contains__(self, data_hora):
        """
        Verifica se a data (considera-se apenas o dia da semana) e hora estão contidas no intervalo.

        @param data_hora: A data e hora (a data em si será desprezada, considerando-se apenas o dia da semana)
        @return: True se estiver contido, False caso contrário.
        """
        return self.data_hora_inicio <= data_hora <= self.data_hora_fim

    def clean(self):
        super().clean()
        if self.data_hora_inicio is not None and self.data_hora_fim is not None:
            if self.data_hora_fim < self.data_hora_inicio + CONSULTA_DURACAO_MAXIMA:
                raise ValidationError(
                    "O fim do intervalo deve ser posterior ao início por, pelo menos, %(antecedencia)s minutos.",
                    params={"antecedencia": CONSULTA_DURACAO_MAXIMA.total_seconds() // 60},
                    code="intervalo_fim_nao_distante_suficiente",
                )

            # Desconsiderar segundos e microssegundos
            self.data_hora_inicio = self.data_hora_inicio.replace(minute=0, second=0, microsecond=0)
            self.data_hora_fim = self.data_hora_fim.replace(minute=0, second=0, microsecond=0)

            if hasattr(self, "psicologo") and self.psicologo:
                # Verificar se há sobreposição de intervalos
                intervalos = self.psicologo.disponibilidade.exclude(pk=self.pk if self.pk else None)

                for intervalo in intervalos:
                    if (
                        intervalo.data_hora_inicio in self or intervalo.data_hora_fim in self or
                        self.data_hora_inicio in intervalo or self.data_hora_fim in intervalo
                    ):
                        raise ValidationError(
                            "Este intervalo sobrepõe este outro intervalo: %(intervalo)s",
                            params={"intervalo": intervalo},
                            code="sobreposicao_intervalos",
                        )
        

class EstadoConsulta(models.TextChoices):
    SOLICITADA = "SOLICITADA", "Solicitada"
    CONFIRMADA = "CONFIRMADA", "Confirmada"
    CANCELADA = "CANCELADA", "Cancelada"
    EM_ANDAMENTO = "EM_ANDAMENTO", "Em andamento"
    FINALIZADA = "FINALIZADA", "Finalizada"
    __empty__ = "Estado"


class Consulta(models.Model):
    data_hora_solicitada = models.DateTimeField(
        "Data e hora em que a consulta foi solicitada",
        # Essa linha de auto_now_add talvez precise mudar quando formos implementar fuso-horários diferentes.
        # Ler a segunda "Note" em:
        # https://docs.djangoproject.com/en/5.1/ref/models/fields/#django.db.models.DateField.auto_now_add
        auto_now_add=True,
    )
    data_hora_agendada = models.DateTimeField(
        "Data e hora agendadas para a consulta",
        validators=[validate_data_hora_agendada],
    )
    duracao = models.IntegerField(
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

        if self.data_hora_agendada < timezone.now() + CONSULTA_ANTECEDENCIA_MINIMA:
            raise ValidationError({
                                      "data_hora_agendada": f"A consulta deve ser agendada com, no mínimo, {CONSULTA_ANTECEDENCIA_MINIMA.total_seconds() // 60} minutos de antecedência."})
        elif hasattr(self, "psicologo") and not self.psicologo.esta_agendavel_em(self.data_hora_agendada):
            raise ValidationError({"data_hora_agendada": "O psicólogo não tem disponibilidade nessa data e horário"})
        elif hasattr(self, "paciente") and self.paciente.ja_tem_consulta_em(self.data_hora_agendada):
            raise ValidationError({
                                      "data_hora_agendada": "O paciente já tem uma consulta marcada que tomaria o tempo dessa que se deseja agendar"})

    def __str__(self):
        return f"Consulta {self.estado.upper()} agendada para {timezone.localtime(self.data_hora_agendada):%d/%m/%Y %H:%M} com {self.paciente.nome} e {self.psicologo.nome_completo}"
