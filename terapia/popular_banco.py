def popular_especializacoes(sender, **kwargs):
    from .models import Especializacao

    Especializacao.objects.bulk_create(
        [
            Especializacao("Transtornos de Ansiedade", "Atuação em avaliações e terapias para quadros ansiosos."),
            Especializacao("Depressão e Transtornos de Humor", "Intervenções em depressão e variações de humor."),
            Especializacao("Trauma e Estresse Pós-Traumático (TEPT)", "Apoio a vítimas de traumas e estresse agudo."),
            Especializacao("Transtornos Alimentares", "Tratamento de anorexia, bulimia e compulsão alimentar."),
            Especializacao("Transtornos de Personalidade", "Terapias para diferentes perfis de personalidade."),
            Especializacao("Vícios e Dependência Química", "Intervenções em dependência de substâncias."),
            Especializacao("Crescimento Pessoal", "Processos de autoconhecimento e desenvolvimento."),
            Especializacao("Luto e Perdas", "Apoio em situações de luto e transições."),
            Especializacao("Dinâmicas Interpessoais", "Estudo das relações e papéis sociais."),
            Especializacao("Relacionamentos Amorosos", "Terapias de casal e mediação de conflitos afetivos."),
            Especializacao("Terapia de Casal", "Foco na comunicação e parceria entre cônjuges."),
            Especializacao("Terapia Familiar", "Atendimento de famílias e sistemas familiares."),
            Especializacao("Conflitos Interpessoais", "Mediação e resolução de conflitos entre indivíduos."),
            Especializacao("Psicologia do Amor", "Estudo das dinâmicas amorosas e afetivas."),
            Especializacao("Psicologia da Infância", "Intervenções em desenvolvimento infantil."),
            Especializacao("Psicologia Parental", "Apoio a pais em práticas de criação e educação."),
            Especializacao("Áreas Institucionais e Contextuais", "Atuação em contextos organizados e comunitários."),
            Especializacao("Psicologia Hospitalar", "Suporte emocional em ambientes de saúde."),
            Especializacao("Psicologia Organizacional", "Análise de comportamento em empresas."),
            Especializacao("Psicologia do Trabalho", "Bem-estar e desempenho no ambiente laboral."),
            Especializacao("Psicologia Escolar e Educacional", "Intervenções no contexto escolar."),
            Especializacao("Psicologia Social e Comunitária", "Projetos e pesquisas em comunidades."),
            Especializacao("Psicologia da Saúde", "Promoção de saúde mental e prevenção."),
            Especializacao("Psicologia Infantil", "Atendimento focado em crianças."),
            Especializacao("Psicologia do Adolescente", "Apoio ao desenvolvimento na adolescência."),
            Especializacao("Psicologia do Adulto", "Terapias voltadas ao público adulto."),
            Especializacao("Psicologia Geriátrica", "Cuidados em saúde mental do idoso."),
        ]
    )


def popular_usuarios(sender, **kwargs):
    from django.contrib.auth import get_user_model
    Usuario = get_user_model()

    dados = [
        {"email": "joao.silva@gmail.com", "password": "joao.silva"},
        {"email": "maria.oliveira@gmail.com", "password": "maria.oliveira"},
        {"email": "pedro.santos@gmail.com", "password": "pedro.santos"},
        {"email": "ana.costa@gmail.com", "password": "ana.costa"},
        {"email": "lucas.almeida@gmail.com", "password": "lucas.almeida"},
        {"email": "paciente.teste@gmail.com", "password": "paciente.teste"},
        {"email": "admin@gmail.com", "password": "admin", "is_staff": True, "is_superuser": True},
    ]

    for item in dados:
        user, created = Usuario.objects.get_or_create(
            email=item["email"],
            defaults={
                "is_active": item.get("is_active", True),
                "is_staff": item.get("is_staff", False),
                "is_superuser": item.get("is_superuser", False),
            }
        )
        if created:
            user.set_password(item["password"])
            user.save()


def popular_psicologos(sender, **kwargs):
    from .models import Psicologo
    import random
    from django.contrib.auth import get_user_model
    Usuario = get_user_model()

    dados = [
        {
            "nome_completo": "João Silva",
            "crp": "01/12345",
            "usuario": Usuario.objects.get(email="joao.silva@gmail.com"),
            "valor_consulta": round(random.uniform(100, 300), 0),
            "sobre_mim": "Tenho ampla experiência em diversas áreas da psicologia e estou aqui para ajudar você a superar seus desafios.",
            "especializacoes": [1, 2, 3, 4, 5],  # IDs das especializações
        },
        {
            "nome_completo": "Maria Oliveira",
            "crp": "02/67890",
            "usuario": Usuario.objects.get(email="maria.oliveira@gmail.com"),
            "valor_consulta": round(random.uniform(100, 300), 0),
            "sobre_mim": "Sou especialista em terapia familiar e de casal, e meu objetivo é fortalecer os laços e resolver conflitos.",
            "especializacoes": [6, 7, 8, 9, 10],  # IDs das especializações
            "foto": "psicologos/fotos/maria.oliveira.jpg",
        },
        {
            "nome_completo": "Pedro Santos",
            "crp": "03/11223",
            "usuario": Usuario.objects.get(email="pedro.santos@gmail.com"),
            "valor_consulta": round(random.uniform(100, 300), 0),
            "sobre_mim": "Trabalho com psicologia organizacional e do trabalho, ajudando pessoas a alcançarem seu potencial no ambiente profissional.",
            "especializacoes": [11, 12, 13, 14, 15],  # IDs das especializações
        },
        {
            "nome_completo": "Ana Costa",
            "crp": "04/44556",
            "usuario": Usuario.objects.get(email="ana.costa@gmail.com"),
            "valor_consulta": round(random.uniform(100, 300), 0),
            "sobre_mim": "Atuo com psicologia infantil e desenvolvimento pessoal, ajudando crianças e adultos a crescerem emocionalmente.",
            "especializacoes": [16, 17, 18, 19, 20],  # IDs das especializações
        },
        {
            "nome_completo": "Lucas Almeida",
            "crp": "05/77889",
            "usuario": Usuario.objects.get(email="lucas.almeida@gmail.com"),
            "valor_consulta": round(random.uniform(100, 300), 0),
            "sobre_mim": "Tenho experiência no tratamento de transtornos de ansiedade e estou aqui para oferecer suporte e acolhimento.",
            "especializacoes": [21, 22, 23, 24, 25],  # IDs das especializações
        },
    ]

    for item in dados:
        psicologo, created = Psicologo.objects.get_or_create(
            crp=item["crp"],
            defaults={
                "nome_completo": item["nome_completo"],
                "usuario": item["usuario"],
                "valor_consulta": item["valor_consulta"],
                "sobre_mim": item["sobre_mim"],
                "foto": item.get("foto"),
            }
        )
        if created:
            psicologo.especializacoes.set(item["especializacoes"])
            psicologo.full_clean()
            psicologo.save()


def popular_pacientes(sender, **kwargs):
    from .models import Paciente
    from django.contrib.auth import get_user_model
    Usuario = get_user_model()

    dados = [
        {"nome": "Paciente Teste", "cpf": "482.763.280-40", "usuario": Usuario.objects.get(email="paciente.teste@gmail.com")},
    ]

    for item in dados:
        Paciente.objects.get_or_create(
            cpf=item["cpf"],
            defaults={"nome": item["nome"], "usuario": item["usuario"]}
        )


def popular_tudo(sender, **kwargs):
    funcoes_de_popular = [
        popular_usuarios,
        popular_especializacoes,
        popular_psicologos,
        popular_pacientes,
    ]
    for funcao in funcoes_de_popular:
        funcao(sender, **kwargs)
