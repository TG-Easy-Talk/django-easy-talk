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








disp1 = [
    {
        "dia_semana": 2,
        "intervalos": [
            {"horario_inicio": "08:00", "horario_fim": "12:00"},
            {"horario_inicio": "14:00", "horario_fim": "18:00"}
        ]
    },
    {
        "dia_semana": 3,
        "intervalos": [
            {"horario_inicio": "08:00", "horario_fim": "12:00"},
            {"horario_inicio": "14:00", "horario_fim": "18:00"}
        ]
    },
    {
        "dia_semana": 4,
        "intervalos": [
            {"horario_inicio": "08:00", "horario_fim": "12:00"},
            {"horario_inicio": "14:00", "horario_fim": "18:00"},
            {"horario_inicio": "19:00", "horario_fim": "21:00"}
        ]
    },
    {
        "dia_semana": 5,
        "intervalos": [
            {"horario_inicio": "08:00", "horario_fim": "12:00"},
            {"horario_inicio": "14:00", "horario_fim": "18:00"}
        ]
    },
    {
        "dia_semana": 6,
        "intervalos": [
            {"horario_inicio": "08:00", "horario_fim": "12:00"},
            {"horario_inicio": "14:00", "horario_fim": "18:00"}
        ]
    }
]

disp2 = [
    {
        "dia_semana": 6,
        "intervalos": [
            {"horario_inicio": "08:00", "horario_fim": "12:00"},
        ]
    },
    {
        "dia_semana": 1,
        "intervalos": [
            {"horario_inicio": "08:00", "horario_fim": "12:00"},
            {"horario_inicio": "15:00", "horario_fim": "18:00"},
        ]
    },
]

disp3 = [
    {
        "dia_semana": 3,
        "intervalos": [
            {"horario_inicio": "08:00", "horario_fim": "12:00"},
            {"horario_inicio": "14:00", "horario_fim": "15:00"},
            {"horario_inicio": "17:00", "horario_fim": "20:00"},
        ]
    },
]

disp4 = [
    {
        "dia_semana": 3,
        "intervalos": [
            {"horario_inicio": "17:00", "horario_fim": "20:00"},
            {"horario_inicio": "08:00", "horario_fim": "12:00"},
            {"horario_inicio": "14:00", "horario_fim": "15:00"},
        ]
    },
]

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
            "disponibilidade": disp2,
        },
        {
            "nome_completo": "Maria Oliveira",
            "crp": "02/67890",
            "usuario": Usuario.objects.get(email="maria.oliveira@gmail.com"),
            "valor_consulta": round(random.uniform(100, 300), 0),
            "sobre_mim": "Sou especialista em terapia familiar e de casal, e meu objetivo é fortalecer os laços e resolver conflitos.",
            "especializacoes": [6, 7, 8, 9, 10],  # IDs das especializações
            "foto": "psicologos/fotos/maria.oliveira.jpg",
            "disponibilidade": disp1,
        },
        {
            "nome_completo": "Pedro Santos",
            "crp": "03/11223",
            "usuario": Usuario.objects.get(email="pedro.santos@gmail.com"),
            "valor_consulta": round(random.uniform(100, 300), 0),
            "sobre_mim": "Trabalho com psicologia organizacional e do trabalho, ajudando pessoas a alcançarem seu potencial no ambiente profissional.",
            "especializacoes": [11, 12, 13, 14, 15],  # IDs das especializações
            "disponibilidade": disp3,
        },
        {
            "nome_completo": "Ana Costa",
            "crp": "04/44556",
            "usuario": Usuario.objects.get(email="ana.costa@gmail.com"),
            "valor_consulta": round(random.uniform(100, 300), 0),
            "sobre_mim": "Atuo com psicologia infantil e desenvolvimento pessoal, ajudando crianças e adultos a crescerem emocionalmente.",
            "especializacoes": [16, 17, 18, 19, 20],  # IDs das especializações
            "disponibilidade": disp4,
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
                "disponibilidade": item.get("disponibilidade"),
            }
        )
        if created:
            psicologo.especializacoes.set(item["especializacoes"])











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










funcoes_de_popular = [popular_usuarios, popular_especializacoes, popular_psicologos, popular_pacientes]
