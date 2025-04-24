from django.apps import AppConfig
from django.db.models.signals import post_migrate


def popular_especializacoes(sender, **kwargs):
    from .models import Especializacao

    dados = [
        {"titulo": "Transtornos de Ansiedade", "descricao": "Atuação em avaliações e terapias para quadros ansiosos."},
        {"titulo": "Depressão e Transtornos de Humor", "descricao": "Intervenções em depressão e variações de humor."},
        {"titulo": "Trauma e Estresse Pós-Traumático (TEPT)",
         "descricao": "Apoio a vítimas de traumas e estresse agudo."},
        {"titulo": "Transtornos Alimentares", "descricao": "Tratamento de anorexia, bulimia e compulsão alimentar."},
        {"titulo": "Transtornos de Personalidade", "descricao": "Terapias para diferentes perfis de personalidade."},
        {"titulo": "Vícios e Dependência Química", "descricao": "Intervenções em dependência de substâncias."},
        {"titulo": "Crescimento Pessoal", "descricao": "Processos de autoconhecimento e desenvolvimento."},
        {"titulo": "Luto e Perdas", "descricao": "Apoio em situações de luto e transições."},
        {"titulo": "Dinâmicas Interpessoais", "descricao": "Estudo das relações e papéis sociais."},
        {"titulo": "Relacionamentos Amorosos", "descricao": "Terapias de casal e mediação de conflitos afetivos."},
        {"titulo": "Terapia de Casal", "descricao": "Foco na comunicação e parceria entre cônjuges."},
        {"titulo": "Terapia Familiar", "descricao": "Atendimento de famílias e sistemas familiares."},
        {"titulo": "Conflitos Interpessoais", "descricao": "Mediação e resolução de conflitos entre indivíduos."},
        {"titulo": "Psicologia do Amor", "descricao": "Estudo das dinâmicas amorosas e afetivas."},
        {"titulo": "Psicologia da Infância", "descricao": "Intervenções em desenvolvimento infantil."},
        {"titulo": "Psicologia Parental", "descricao": "Apoio a pais em práticas de criação e educação."},
        {"titulo": "Áreas Institucionais e Contextuais",
         "descricao": "Atuação em contextos organizados e comunitários."},
        {"titulo": "Psicologia Hospitalar", "descricao": "Suporte emocional em ambientes de saúde."},
        {"titulo": "Psicologia Organizacional", "descricao": "Análise de comportamento em empresas."},
        {"titulo": "Psicologia do Trabalho", "descricao": "Bem-estar e desempenho no ambiente laboral."},
        {"titulo": "Psicologia Escolar e Educacional", "descricao": "Intervenções no contexto escolar."},
        {"titulo": "Psicologia Social e Comunitária", "descricao": "Projetos e pesquisas em comunidades."},
        {"titulo": "Psicologia da Saúde", "descricao": "Promoção de saúde mental e prevenção."},
        {"titulo": "Psicologia Infantil", "descricao": "Atendimento focado em crianças."},
        {"titulo": "Psicologia do Adolescente", "descricao": "Apoio ao desenvolvimento na adolescência."},
        {"titulo": "Psicologia do Adulto", "descricao": "Terapias voltadas ao público adulto."},
        {"titulo": "Psicologia Geriátrica", "descricao": "Cuidados em saúde mental do idoso."},
    ]

    for item in dados:
        Especializacao.objects.get_or_create(
            titulo=item["titulo"],
            defaults={"descricao": item["descricao"]}
        )


class TerapiaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'terapia'
    verbose_name = 'Terapia'

    def ready(self):
        import terapia.signals
        post_migrate.connect(popular_especializacoes, sender=self)
