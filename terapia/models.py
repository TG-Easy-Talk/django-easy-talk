from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from terapia.utils.crp import validate_crp
from terapia.utils.cpf import validate_cpf
from terapia.utils.availability import (
    check_psicologo_disponibilidade,
    validate_disponibilidade
)
from terapia.utils.validators import (
    validate_future_datetime,
    validate_duracao_range,
    validate_valor_consulta,
)


class Paciente(models.Model):
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
        if hasattr(self.usuario, 'psicologo'):
            raise ValidationError("Este usuário já está relacionado a um psicólogo.")

    def __str__(self):
        return self.nome
    
    def get_url_foto_propria_ou_padrao(self):
        if self.foto:
            return self.foto.url
        return settings.STATIC_URL + "img/foto_de_perfil.jpg"


class Especializacao(models.Model):
    titulo = models.CharField("Título", max_length=100, unique=True)
    descricao = models.TextField("Descrição")

    class Meta:
        verbose_name = "Especialização"
        verbose_name_plural = "Especializações"

    def __str__(self):
        return self.titulo


class Psicologo(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='psicologo'
    )
    nome_completo = models.CharField("Nome Completo", max_length=50)
    crp = models.CharField("CRP", max_length=20, unique=True, validators=[validate_crp])
    foto = models.ImageField("Foto", upload_to='psicologos/fotos/', blank=True, null=True)
    sobre_mim = models.TextField("Sobre Mim", blank=True)
    valor_consulta = models.DecimalField(
        "Valor da Consulta",
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[
            validate_valor_consulta,
        ],
        help_text="Entre R$ 20,00 e R$ 4.999,99",
    )
    disponibilidade = models.JSONField(
        "Disponibilidade",
        blank=True,
        null=True,
        validators=[validate_disponibilidade]
    )
    especializacoes = models.ManyToManyField(
        Especializacao,
        verbose_name="Especializações",
        related_name='psicologos',
        blank=True,
    )

    @property
    def primeiro_nome(self):
        return self.nome_completo.split()[0]


    class Meta:
        verbose_name = "Psicólogo"
        verbose_name_plural = "Psicólogos"


    def clean(self):
        super().clean()
        # Checar se já há paciente relacionado
        if hasattr(self.usuario, 'paciente'):
            raise ValidationError("Este usuário já está relacionado a um paciente.")


    def __str__(self):
        return self.nome_completo
    

    def get_absolute_url(self):
        return reverse("perfil", kwargs={"pk": self.pk})
    

    def get_url_foto_propria_ou_padrao(self):
        if self.foto:
            return self.foto.url
        return settings.STATIC_URL + "img/foto_de_perfil.jpg"
    

    def get_intervalos_do_dia(self, dia_semana):
        if (1 <= dia_semana <= 7) is False:
            raise ValueError("O dia da semana deve ser um número entre 1 (domingo) e 7 (sábado).")

        for disp in self.disponibilidade:
            if disp["dia_semana"] == dia_semana:
                return disp["intervalos"]
        return []


    def get_numero_maximo_intervalos(self):
        return max(len(disp["intervalos"]) for disp in self.disponibilidade)


    def get_matriz_disponibilidade(self):
        """
        Monta uma matriz de disponibilidade com base no JSON de disponibilidade,
        onde cada coluna representa um dia da semana.
        """
        numero_maximo_intervalos = self.get_numero_maximo_intervalos()
        matriz = []
        
        for i in range(1, 8):
            intervalos_do_dia = self.get_intervalos_do_dia(i)
            horarios_do_dia = []

            for intervalo in intervalos_do_dia:
                horarios_do_dia.append(f"{intervalo['horario_inicio']} - {intervalo['horario_fim']}")

            if len(horarios_do_dia) < numero_maximo_intervalos:
                horarios_do_dia += ["-"] * (numero_maximo_intervalos - len(horarios_do_dia))

            matriz.append(horarios_do_dia)

        # Transpor a matriz
        qtd_colunas_transp = 7
        qtd_linhas_transp = numero_maximo_intervalos
        matriz_transp = [[0 for _ in range(qtd_colunas_transp)] for _ in range(qtd_linhas_transp)]

        for i, linha in enumerate(matriz):
            for j, valor in enumerate(linha):
                matriz_transp[j][i] = matriz[i][j]

        return matriz_transp
    

    def get_html_corpo_tabela_disponibilidade(self):
        """
        Monta o HTML do corpo da tabela de disponibilidade do psicólogo.
        """
        tbody_inner_html = ""

        for linha in self.get_matriz_disponibilidade():
            tbody_inner_html += "<tr>"

            for intervalo in linha:
                tbody_inner_html += f"<td>{intervalo}</td>"

            tbody_inner_html += "</tr>"

        return tbody_inner_html


class EstadoConsulta(models.TextChoices):
    SOLICITADA = 'SOLICITADA', 'Solicitada'
    CONFIRMADA = 'CONFIRMADA', 'Confirmada'
    CANCELADA = 'CANCELADA', 'Cancelada'
    EM_ANDAMENTO = 'EM_ANDAMENTO', 'Em andamento'
    FINALIZADA = 'FINALIZADA', 'Finalizada'


class Consulta(models.Model):
    data_hora_marcada = models.DateTimeField(
        "Data e Hora Marcada",
        validators=[validate_future_datetime],
    )
    duracao = models.IntegerField(
        "Duração (minutos)",
        validators=[validate_duracao_range],
    )
    estado = models.CharField(
        "Estado",
        max_length=20,
        choices=EstadoConsulta.choices,
        default=EstadoConsulta.SOLICITADA,
    )
    anotacoes = models.TextField("Anotações", blank=True)
    checklist_tarefas = models.TextField("Checklist de Tarefas", blank=True)
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='consultas')
    psicologo = models.ForeignKey(Psicologo, on_delete=models.CASCADE, related_name='consultas')

    class Meta:
        verbose_name = "Consulta"
        verbose_name_plural = "Consultas"

    def clean(self):
        super().clean()
        if not check_psicologo_disponibilidade(self.psicologo, self.data_hora_marcada):
            raise ValidationError("O psicólogo não tem disponibilidade nessa data e horário")

    def validate_unique(self, exclude=None):
        super().validate_unique(exclude=exclude)
        # Conflito de horário
        qs = Consulta.objects.filter(
            paciente=self.paciente,
            data_hora_marcada=self.data_hora_marcada
        ).exclude(pk=self.pk or None)
        if qs.exists():
            raise ValidationError({
                'data_hora_marcada': 'Você já possui uma consulta agendada nesse horário'
            })

    def __str__(self):
        return f"Consulta em {self.data_hora_marcada:%Y-%m-%d %H:%M} com {self.paciente.nome} e {self.psicologo.nome_completo}"
    