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
from .constants import CONSULTA_DURACAO_MAXIMA, CONSULTA_ANTECEDENCIA_MINIMA, CONSULTA_ANTECEDENCIA_MAXIMA
from datetime import datetime, date, timedelta


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

    objects = models.Manager()
    completos = PsicologoCompletosManager()

    class Meta:
        verbose_name = "Psicólogo"
        verbose_name_plural = "Psicólogos"

    @staticmethod
    def _align_to_slot(dt):
        """Alinha um datetime para o “degrau” da CONSULTA_DURACAO_MAXIMA (minutos)."""
        step = int(CONSULTA_DURACAO_MAXIMA.total_seconds() // 60)
        return dt.replace(minute=(dt.minute // step) * step, second=0, microsecond=0)

    def _to_template_week(self, dt):
        """
        Converte um datetime real (aware/naive) para a semana-modelo (01–08/07/2024),
        preservando weekday/hora/minuto e normalizando para a timezone atual.
        """
        tz = timezone.get_current_timezone()
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, tz)
        dt_local = timezone.localtime(dt, tz)
        return datetime(
            2024, 7, dt_local.isoweekday(),  # 1..7 (seg..dom)
            dt_local.hour, dt_local.minute, tzinfo=tz
        )

    def _template_range_for(self, start_dt):
        """
        Para um início real, retorna (start_t, end_t) na semana-modelo
        garantindo que end_t > start_t mesmo quando a consulta cruza a “segunda final”.
        """
        start_t = self._to_template_week(start_dt)
        end_real = start_dt + CONSULTA_DURACAO_MAXIMA
        end_t = self._to_template_week(end_real)
        if end_t <= start_t:
            end_t = end_t + timedelta(days=7)
        return start_t, end_t

    def _intervalos_para_data(self, dia_real):
        """
        Para um 'date' real, projeta todos os IntervaloDisponibilidade (semana-modelo)
        para esse dia. Retorna lista de pares (inicio_real, fim_real) no fuso atual.
        """
        tz = timezone.get_current_timezone()
        monday = dia_real - timedelta(days=dia_real.isoweekday() - 1)
        proj = []
        for it in self.disponibilidade.all():
            ini_loc = it.data_hora_inicio_local
            fim_loc = it.data_hora_fim_local

            delta_ini = ini_loc.isoweekday() - 1
            base_ini = datetime.combine(monday + timedelta(days=delta_ini), ini_loc.timetz())
            base_ini = base_ini if base_ini.tzinfo else timezone.make_aware(base_ini, tz)

            if fim_loc.isoweekday() >= ini_loc.isoweekday():
                delta_fim = fim_loc.isoweekday() - 1
                base_fim = datetime.combine(monday + timedelta(days=delta_fim), fim_loc.timetz())
            else:
                delta_fim = fim_loc.isoweekday() - 1 + 7
                base_fim = datetime.combine(monday + timedelta(days=delta_fim), fim_loc.timetz())

            base_fim = base_fim if base_fim.tzinfo else timezone.make_aware(base_fim, tz)
            proj.append((base_ini, base_fim))
        return proj

    def _get_intervalos_do_mais_proximo_ao_mais_distante_no_futuro(self, dias_no_futuro=60):
        """
        Gera, a partir de hoje, as janelas reais de disponibilidade (projetadas) por dia,
        até um limite de 'dias_no_futuro'.
        """
        tz = timezone.get_current_timezone()
        hoje = timezone.localtime(timezone.now(), tz).date()
        for i in range(dias_no_futuro + 1):
            dia = hoje + timedelta(days=i)
            for inicio, fim in self._intervalos_para_data(dia):
                yield inicio, fim

    @property
    def primeiro_nome(self):
        return self.nome_completo.split()[0]

    @property
    @admin.display(boolean=True)
    def esta_com_perfil_completo(self):
        """
        Tem valor de consulta, ao menos uma especialização e alguma disponibilidade?
        """
        return bool(
            self.valor_consulta and
            self.especializacoes.exists() and
            self.disponibilidade.exists()
        )

    @property
    def proxima_data_hora_agendavel(self):
        """
        Retorna o próximo início de consulta disponível (datetime aware) considerando:
        - disponibilidade projetada para as próximas datas;
        - passo = CONSULTA_DURACAO_MAXIMA;
        - antecedência mínima;
        - conflitos (psicólogo/paciente) via esta_agendavel_em().
        """
        if not self.disponibilidade.exists():
            return None

        tz = timezone.get_current_timezone()
        agora = timezone.localtime(timezone.now(), tz)
        step_min = int(CONSULTA_DURACAO_MAXIMA.total_seconds() // 60)

        for inicio, fim in self._get_intervalos_do_mais_proximo_ao_mais_distante_no_futuro(dias_no_futuro=60):
            inicio_considerado = max(inicio, agora + CONSULTA_ANTECEDENCIA_MINIMA)
            cur = self._align_to_slot(inicio_considerado)

            limite_inicio = fim - CONSULTA_DURACAO_MAXIMA
            while cur <= limite_inicio:
                if self.esta_agendavel_em(cur):
                    return cur
                cur += timedelta(minutes=step_min)
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
        start_t, end_t = self._template_range_for(data_hora)
        try:
            return self.disponibilidade.get(
                data_hora_inicio__lte=start_t,
                data_hora_fim__gte=end_t,
            )
        except IntervaloDisponibilidade.DoesNotExist:
            return None

    def _tem_intervalo_em(self, data_hora):
        start_t, end_t = self._template_range_for(data_hora)
        return self.disponibilidade.filter(
            data_hora_inicio__lte=start_t,
            data_hora_fim__gte=end_t,
        ).exists()

    def esta_agendavel_em(self, data_hora):
        """
        Verifica se o psicólogo tem disponibilidade para uma consulta que começa na
        data e hora enviadas.
        
        @param data_hora: Data e hora em que a consulta começa.
        @return: True se o psicólogo tem disponibilidade, False caso contrário.
        """
        return bool(
            data_hora >= timezone.now() + CONSULTA_ANTECEDENCIA_MINIMA and
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
        return self.data_hora_inicio.astimezone(tz=timezone.get_current_timezone())

    @property
    def data_hora_fim_local(self):
        return self.data_hora_fim.astimezone(tz=timezone.get_current_timezone())

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
                    f"O fim do intervalo deve ser posterior ao início por, pelo menos, {CONSULTA_DURACAO_MAXIMA.total_seconds() // 60} minutos.")

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
                        raise ValidationError(f"Este intervalo sobrepõe este outro intervalo: {intervalo}")


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
        constraints = [
            models.UniqueConstraint(
                fields=["psicologo", "data_hora_agendada"],
                name="uniq_consulta_psicologo_inicio",
            )
        ]

    def clean(self):
        super().clean()

        if self.data_hora_agendada < timezone.now() + CONSULTA_ANTECEDENCIA_MINIMA:
            raise ValidationError({
                "data_hora_agendada": f"A consulta deve ser agendada com, no mínimo, {CONSULTA_ANTECEDENCIA_MINIMA.total_seconds() // 60} minutos de antecedência."
            })
        elif hasattr(self, "psicologo") and not self.psicologo.esta_agendavel_em(self.data_hora_agendada):
            raise ValidationError({"data_hora_agendada": "O psicólogo não tem disponibilidade nessa data e horário"})
        elif hasattr(self, "paciente") and self.paciente.ja_tem_consulta_em(self.data_hora_agendada):
            raise ValidationError({
                "data_hora_agendada": "O paciente já tem uma consulta marcada que tomaria o tempo dessa que se deseja agendar"
            })

    def __str__(self):
        return f"Consulta {self.estado.upper()} agendada para {timezone.localtime(self.data_hora_agendada):%d/%m/%Y %H:%M} com {self.paciente.nome} e {self.psicologo.nome_completo}"
