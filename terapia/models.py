from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.contrib import admin
from django.utils import timezone
from terapia.utils.crp import validate_crp
from terapia.utils.cpf import validate_cpf
from terapia.utils.availability import (
    validate_disponibilidade,
    esta_no_intervalo,
    combinar_data_com_str_horario,
    get_horas_intervalo,
)
from terapia.utils.validators import (
    validate_data_hora_agendada,
    validate_valor_consulta,
)
from datetime import timedelta
from .constants import CONSULTA_DURACAO_MAXIMA, CONSULTA_ANTECEDENCIA_MAXIMA, CONSULTA_ANTECEDENCIA_MINIMA


class BasePacienteOuPsicologo(models.Model):
    def ja_tem_consulta_em(self, data_hora):
        """
        Verifica se o psicólogo tem um intervalo de disponibilidade no qual se
        encaixa uma consulta que começa na data e hora enviadas.
        
        @param data_hora: Data e hora em que a consulta começa.
        @return: True se a consulta se encaixa no intervalo, False caso contrário.
        """
        return self.consultas.filter(
            Q(data_hora_agendada__gt = data_hora - CONSULTA_DURACAO_MAXIMA) &
            Q(data_hora_agendada__lt = data_hora + CONSULTA_DURACAO_MAXIMA) &
            ~ Q(estado=EstadoConsulta.CANCELADA) # Desconsiderar consultas canceladas
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
        on_delete=models.CASCADE,
        related_name='paciente'
    )
    nome = models.CharField("Nome", max_length=50)
    cpf = models.CharField("CPF", max_length=14, unique=True, validators=[validate_cpf])
    foto = models.ImageField("Foto", upload_to='pacientes/fotos/', blank=True, null=True)

    class Meta:
        verbose_name = "Paciente"
        verbose_name_plural = "Pacientes"

    def clean(self):
        super().clean()
        # Primeiro, verifica se o usuário já é psicólogo
        if self.usuario.is_psicologo:
            raise ValidationError("Este usuário já está relacionado a um psicólogo.")

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
            ~ Q(disponibilidade__exact=[])
        )
    
    def get_queryset(self):
        return super().get_queryset().filter(self.get_filtros()).distinct()

class Psicologo(BasePacienteOuPsicologo):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='psicologo',
    )
    nome_completo = models.CharField("Nome Completo", max_length=50)
    crp = models.CharField("CRP", max_length=20, unique=True, validators=[validate_crp])
    foto = models.ImageField("Foto", upload_to='psicologos/fotos/', blank=True, null=True)
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
    disponibilidade = models.JSONField(
        "Disponibilidade",
        default=list,
        blank=True,
        validators=[validate_disponibilidade],
    )
    especializacoes = models.ManyToManyField(
        Especializacao,
        verbose_name="Especializações",
        related_name='psicologos',
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
        """
        Retorna True se o psicólogo tem perfil completo, ou seja,
        se possui valor de consulta, pelo menos uma especialização e disponibilidade definida.
        """
        return bool(
            self.valor_consulta and
            self.especializacoes.exists() and
            self.disponibilidade
        )
    
    @property
    def proxima_data_hora_agendavel(self):
        """
        Retorna a data e hora agendáveis mais próximas do psicólogo.
        """
        if not self.disponibilidade:
            return None

        i = 0
        agora = timezone.now()
        suposta_data_hora_agendavel_mais_proxima = agora + CONSULTA_ANTECEDENCIA_MINIMA

        if agora.day < suposta_data_hora_agendavel_mais_proxima.day:
            i += 1

        while i < CONSULTA_ANTECEDENCIA_MAXIMA.days:
            hoje = agora.date() + timedelta(days=i)
            dia_semana = hoje.isoweekday() % 7 + 1  # 1 (domingo) a 7 (sábado)

            for intervalo in self._get_intervalos_do_dia_semana(dia_semana):
                for hora in get_horas_intervalo(intervalo):
                    data_hora_inicio = combinar_data_com_str_horario(hoje, f"{hora}:00", agora.tzinfo)

                    if (
                        data_hora_inicio >= suposta_data_hora_agendavel_mais_proxima and
                        not self.ja_tem_consulta_em(data_hora_inicio)
                    ):
                        return data_hora_inicio

            i += 1

        return None

    def clean(self):
        super().clean()
        # Checar se já há paciente relacionado
        if self.usuario.is_paciente:
            raise ValidationError("Este usuário já está relacionado a um paciente.")

        # Ordenar os intervalos de cada dia em ordem cronológica crescente
        if self.disponibilidade:
            for disp in self.disponibilidade:
                intervalos = disp["intervalos"]
                intervalos.sort(key=lambda x: (x["horario_inicio"], x["horario_fim"]))
                disp["intervalos"] = intervalos

    def __str__(self):
        return self.nome_completo

    def get_absolute_url(self):
        return reverse("perfil", kwargs={"pk": self.pk})
    
    def _get_intervalos_do_dia_semana(self, dia_semana):
        """
        Retorna os intervalos de disponibilidade do psicólogo para um dia da semana específico.

        @param dia_semana: Dia da semana (1 = domingo, 7 = sábado).
        @return: Lista de intervalos de disponibilidade ou [] se não houver.
        """
        for disp in self.disponibilidade:
            if disp["dia_semana"] == dia_semana:
                return disp["intervalos"]
        
        return []

    def _get_intervalo_em(self, data_hora):
        """
        Retorna, se houver, o intervalo no qual se encaixa uma consulta que começa
        na data e hora enviadas.
        
        (A consulta deve caber completamente no intervalo para que ele seja retornado).
        
        @param data_hora: Data e hora em que a consulta começa.
        @return: O intervalo no qual a consulta se encaixa, None caso não exista.
        """
        dia_semana = (data_hora.isoweekday() % 7) + 1 # 1 (domingo) a 7 (sábado)
        horario_inicio = timedelta(hours=data_hora.hour, minutes=data_hora.minute)

        intervalo_encontrado = None

        for disp in self.disponibilidade:
            if disp["dia_semana"] == dia_semana:
                for intervalo in disp["intervalos"]:
                    if esta_no_intervalo(horario_inicio, intervalo):
                        intervalo_encontrado = intervalo
        
        if intervalo_encontrado is None:
            return None
        
        horario_fim = horario_inicio + CONSULTA_DURACAO_MAXIMA

        if not esta_no_intervalo(horario_fim, intervalo_encontrado):
            return None
        
        return intervalo_encontrado

    def _tem_intervalo_em(self, data_hora):
        """
        Verifica se o psicólogo tem um intervalo de disponibilidade no qual se
        encaixa uma consulta que começa na data e hora enviadas.
        
        (A consulta deve caber completamente no intervalo para que ele seja válido).

        @param data_hora: Data e hora em que a consulta começa.
        @return: True se a consulta se encaixa no intervalo, False caso contrário.
        """
        intervalo = self._get_intervalo_em(data_hora)
        return False if intervalo is None else True

    def esta_agendavel_em(self, data_hora):
        """
        Verifica se o psicólogo tem disponibilidade para uma consulta que começa na
        data e hora enviadas.
        
        @param data_hora: Data e hora em que a consulta começa.
        @return: True se o psicólogo tem disponibilidade, False caso contrário.
        """
        return bool(
            self.disponibilidade and
            self._tem_intervalo_em(data_hora) and
            not self.ja_tem_consulta_em(data_hora)
        )

class EstadoConsulta(models.TextChoices):
    SOLICITADA = 'SOLICITADA', 'Solicitada'
    CONFIRMADA = 'CONFIRMADA', 'Confirmada'
    CANCELADA = 'CANCELADA', 'Cancelada'
    EM_ANDAMENTO = 'EM_ANDAMENTO', 'Em andamento'
    FINALIZADA = 'FINALIZADA', 'Finalizada'


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
        related_name='consultas',
        limit_choices_to=Psicologo.completos.get_filtros(),
    )

    class Meta:
        verbose_name = "Consulta"
        verbose_name_plural = "Consultas"
        ordering = ['-data_hora_solicitada', '-data_hora_agendada']

    def clean(self):
        super().clean()
        if not self.psicologo.esta_agendavel_em(self.data_hora_agendada):
            raise ValidationError({"data_hora_agendada": "O psicólogo não tem disponibilidade nessa data e horário"})
        if self.paciente.ja_tem_consulta_em(self.data_hora_agendada):
            raise ValidationError({"data_hora_agendada": "O paciente já tem uma consulta marcada que tomaria o tempo dessa que se deseja agendar"})
        
    def __str__(self):
        return f"Consulta {self.estado.upper()} em {self.data_hora_agendada:%d/%m/%Y %H:%M} com {self.paciente.nome} e {self.psicologo.nome_completo}"
    