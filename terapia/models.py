from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from terapia.utils.crp import validate_crp
from terapia.utils.cpf import validate_cpf
from terapia.utils.availability import (
    validate_disponibilidade,
    parse_time,
    esta_no_intervalo,
)
from terapia.utils.validators import (
    validate_uma_hora_antecedencia,
    validate_valor_consulta,
)
from datetime import datetime, timedelta


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
    

    def get_url_foto_propria_ou_padrao(self):
        if self.foto:
            return self.foto.url
        return settings.STATIC_URL + "img/foto_de_perfil.jpg"
    

    def get_intervalo_dessa_hora(self, hora, dia_semana):
        """
        Dentre os intervalos de disponibilidade de um dia da semana específico,
        retorna o intervalo em que a hora enviada está.

        @param hora: Hora a ser verificada (datetime.time)
        @param dia_semana: Dia da semana do intervalo (1 = domingo, 7 = sábado)
        @return: Intervalo em que a hora está ou None se não estiver em nenhum intervalo.
        """
        if self.disponibilidade is None:
            return None

        for disp in self.disponibilidade:
            if disp["dia_semana"] == dia_semana:
                for intervalo in disp["intervalos"]:
                    if esta_no_intervalo(hora, intervalo):
                        return intervalo
        return None


    def tem_disponibilidade_para_essa_data_hora(self, data_hora_marcada):
        """
        Verifica se o psicólogo tem disponibilidade para uma consulta em um determinado dia e horário.
        """
        if self.disponibilidade is None:
            return False
        
        # Verificar se o início da consulta está em algum intervalo
        dia_semana = (data_hora_marcada.isoweekday() % 7) + 1 # 1 (domingo) a 7 (sábado)
        hora_inicio = data_hora_marcada.time()

        intervalo = self.get_intervalo_dessa_hora(hora_inicio, dia_semana)

        if intervalo is None:
            return False
        
        # Verificar se a consulta terminará antes do fim do intervalo
        data_hora_inicio = datetime.combine(datetime.today(), hora_inicio) # Passar para datetime para poder somar 1 hora
        data_hora_final = data_hora_inicio + timedelta(hours=1)
        hora_final = data_hora_final.time()

        return esta_no_intervalo(hora_final, intervalo)


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
        "Data e hora para as quais a consulta foi marcada",
        validators=[validate_uma_hora_antecedencia],
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
        if not self.psicologo.tem_disponibilidade_para_essa_data_hora(self.data_hora_marcada):
            raise ValidationError({"data_hora_marcada": "O psicólogo não tem disponibilidade nessa data e horário"})
        
    def __str__(self):
        return f"Consulta em {self.data_hora_marcada:%d/%m/%Y %H:%M} com {self.paciente.nome} e {self.psicologo.nome_completo}"
    