from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.urls import reverse
from terapia.utils.crp import validate_crp
from terapia.utils.cpf import validate_cpf
from terapia.utils.availability import (
    validate_disponibilidade,
    esta_no_intervalo,
)
from terapia.utils.validators import (
    validate_antecedencia,
    validate_valor_consulta,
)
from datetime import datetime, timedelta
from django.contrib import admin
from .constants import CONSULTA_DURACAO_MAXIMA, CONSULTA_ANTECEDENCIA_MINIMA


class BasePacienteOuPsicologo(models.Model):
    def ja_tem_consulta_que_ocupa_o_tempo(self, consulta):
        """
        Verifica se o psicólogo já tem alguma consulta marcada que tomará tempo da
        consulta que se deseja marcar.
        """
        return self.consultas.filter(
            Q(data_hora_marcada__gt = consulta.data_hora_marcada - CONSULTA_DURACAO_MAXIMA) &
            Q(data_hora_marcada__lt = consulta.data_hora_marcada + CONSULTA_DURACAO_MAXIMA) &
            ~ Q(estado=EstadoConsulta.CANCELADA) & # Desconsiderar consultas canceladas
            ~ Q(pk=consulta.pk) # Desconsiderar a própria consulta
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
    def get_queryset(self):
        return super().get_queryset().filter(
            Q(valor_consulta__isnull=False) &
            Q(especializacoes__isnull=False) &
            ~ Q(disponibilidade__exact=[])
        ).distinct()


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
    def proximo_intervalo_disponivel(self):
        """
        Retorna o próximo intervalo de disponibilidade do psicólogo.
        Se não houver disponibilidade, retorna None.
        """
        pass
        # if not self.disponibilidade:
        #     return None

        # agora = datetime.now()

        # for _ in range(1, 8):
        #     instante = timedelta(hours=agora.hour, minutes=agora.minute) + CONSULTA_ANTECEDENCIA_MINIMA

        #     # Considerar apenas horário, ignorando o dia
        #     if instante >= timedelta(days=1):
        #         instante.days = 0 

        #     dia_semana = (instante.isoweekday() % 7) + 1

        #     intervalo = self.get_intervalo_para_essa_consulta(instante, dia_semana)
            

    class Meta:
        verbose_name = "Psicólogo"
        verbose_name_plural = "Psicólogos"


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
    

    def get_intervalo_para_essa_consulta(self, consulta):
        """
        Retorna o intervalo da disponibilidade em que a consulta se encaixa, se houver.

        @param horario: Horário a ser verificado (timedelta)
        @param dia_semana: Dia da semana do intervalo (1 = domingo, 7 = sábado)
        @return: Intervalo em que a consulta se encaixa ou None se não houver.
        """
        if not self.disponibilidade:
            return None
        
        dhm = consulta.data_hora_marcada
        dia_semana = (dhm.isoweekday() % 7) + 1 # 1 (domingo) a 7 (sábado)
        horario_inicio = timedelta(hours=dhm.hour, minutes=dhm.minute)

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


    def tem_intervalo_para_essa_consulta(self, consulta):
        """
        Retorna True se há algum intervalo de disponibilidade para a consulta que se deseja marcar.
        Caso contrário, retorna False.
        """
        intervalo = self.get_intervalo_para_essa_consulta(consulta)

        if intervalo is None:
            return False
        return True


    def tem_disponibilidade_para_essa_consulta(self, consulta):
        """
        Verifica se o psicólogo tem disponibilidade para uma consulta em um determinado dia e horário.
        """
        return (
            self.disponibilidade and
            self.tem_intervalo_para_essa_consulta(consulta) and
            not self.ja_tem_consulta_que_ocupa_o_tempo(consulta)
        )


class EstadoConsulta(models.TextChoices):
    SOLICITADA = 'SOLICITADA', 'Solicitada'
    CONFIRMADA = 'CONFIRMADA', 'Confirmada'
    CANCELADA = 'CANCELADA', 'Cancelada'
    EM_ANDAMENTO = 'EM_ANDAMENTO', 'Em andamento'
    FINALIZADA = 'FINALIZADA', 'Finalizada'


class Consulta(models.Model):
    data_hora_marcada = models.DateTimeField(
        "Data e hora marcadas para a consulta",
        validators=[validate_antecedencia],
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
    psicologo = models.ForeignKey(Psicologo, on_delete=models.CASCADE, related_name='consultas')

    class Meta:
        verbose_name = "Consulta"
        verbose_name_plural = "Consultas"

    def clean(self):
        super().clean()
        if not self.psicologo.tem_disponibilidade_para_essa_consulta(self):
            raise ValidationError({"data_hora_marcada": "O psicólogo não tem disponibilidade nessa data e horário"})
        if self.paciente.ja_tem_consulta_que_ocupa_o_tempo(self):
            raise ValidationError({"data_hora_marcada": "O paciente já tem uma consulta marcada que tomaria o tempo dessa que se deseja agendar"})
        
    def __str__(self):
        return f"Consulta {self.estado.upper()} em {self.data_hora_marcada:%d/%m/%Y %H:%M} com {self.paciente.nome} e {self.psicologo.nome_completo}"
    