# 🧠 EasyTalk

O EasyTalk é um web app para tratamentos e sessões online de terapia por chat, ligação ou videochamada. Tanto clientes quanto psicólogos podem se cadastrar e utilizar o sistema.

### ⚖️ Justificativa
- Um sistema online de terapia pode ser uma proposta atrativa para pessoas buscando tratamentos psicológicos por conta da facilidade e conveniência, ainda mais com o diferencial de consultas instantâneas.
- É um bom portal de divulgação para os profissionais da área.
- Não há muitos sistemas com essa proposta no mercado atualmente e os que existem são pouco difundidos.

### 💡 **Diferencial**
Haverá a opção de realizar consultas "instantâneas" no sistema, as quais funcionarão assim: o cliente, quando clicar nessa opção, será automaticamente pareado com um psicólogo que esteja disponível no momento para realizar uma consulta. Isso objetiva acelerar e tornar mais conveniente o processo de realizar uma consulta.

### 🎯 Objetivo smart
- Ter o sistema pronto para publicação até o fim de 2025 com pelo menos 200 clientes e 50 psicólogos cadastrados.
- Realizar 3000 consultas até o fim de 2026.

### ✅ Requisitos funcionais
- Cadastro de clientes
- Cadastro de psicólogos
- Personalização de perfil para psicólogos
- Pesquisa e filtragem de psicólogos
- Agendar consultas
- Consultas
- Consultas instantâneas
- Checklist de tarefas de casa dadas pelo psicólogo ao cliente
- Relatórios e anotações das consultas para psicólogos
- Histórico de consultas

### 💰 Termos monetários
O custo de mão de obra estimado é de R$15.000,00.
Se o objetivo smart for alcançado, o payback será de 1 ano.


# 🚀 Funcionalidades

🐍 O projeto é desenvolvido em **Django.**

### 👤 Paciente
- 📝 Criar conta
- 🔍 Pesquisar e filtrar psicólogos para atender suas preferências
- 📅 Agendar uma consulta
- 🎯 Ser pareado automaticamente para uma consulta instantânea
- 📷 Realizar consultas por videochamada, ligação ou chat
- ✅ Visualizar checklist de tarefas de casa dadas pelo psicólogo
- 📖 Acessar histórico de consultas

### 👨‍⚕️ Psicólogo
- 📝 Criar conta
- 🧑‍🎨 Personalizar perfil com suas especializações, preço, sobre mim...
- 🕒 Definir seus horários de disponibilidade
- 💬 Receber solicitações de consultas e realizá-las com pacientes
- 🗒️ Fazer anotações para cada consulta
- 🧾 Montar checklist de tarefas de casa para seu paciente
- 🔎 Visualizar anotações de consultas anteriores


# 🧩 Modelo de Banco de Dados

### 🧾 Entidades

📌 **Usuario**
```
id: long
email: String
senha: String
```

👤 **Cliente**
```
id: long
nome: String
cpf: String
foto: Image
OneToOne para Usuario
```

👨‍⚕️ **Psicologo**
```
id: long
nomeCompleto: String
crp: String
foto: Image
sobreMim: String
valorConsulta: double
OneToOne para Usuario
```

⏰ **IntervaloDisponibilidade**
```
id: long
dataHoraInicio: DateTime
dataHoraFim: DateTime
ForeignKey para Psicologo
```

**📅 Consulta**
```
id: long
dataHoraAgendada: DateTime
duracao: int
estado: EstadoConsulta
anotacoes: String
checklistTarefas: String
ForeignKey para Paciente
ForeignKey para Psicologo
```

**🎓 Especializacao**
```
id: long
titulo: String
descricao: String
ManyToMany para Psicologo
```

### 🔢 Enumeração

**📅 EstadoConsulta**
```
SOLICITADA
CONFIRMADA
CANCELADA
EM_ANDAMENTO
FINALIZADA
```

# 👨‍💻 Dev Team
| Nome | GitHub |
| --- | --- |
| Vinícius dos Santos Andrade | [https://github.com/viniciusdsandrade](https://github.com/viniciusdsandrade) |
| Felipe de Carvalho Santos | [https://github.com/Felipinho5](https://github.com/Felipinho5) |
