# Relatório Completo de Alterações - 22/11/2025

Este relatório detalha todas as intervenções técnicas realizadas no projeto hoje, focadas em arquitetura, segurança, performance e correção de bugs críticos.

## 1. Arquitetura e Refatoração (SOLID) 🏗️

O objetivo foi desacoplar a lógica de negócio dos Models e Views, facilitando testes e manutenção.

*   **Nova Camada de Serviços**:
    *   Criado pacote `terapia.service` (anteriormente `terapia.services`).
    *   **`AgendamentoService`**: Centraliza toda a lógica complexa de disponibilidade, cálculo de horários e verificação de conflitos.
    *   **`ConsultaService`**: Gerencia a criação transacional de consultas.
*   **Refatoração do Model `Psicologo`**:
    *   Métodos como `esta_agendavel_em`, `proxima_data_hora_agendavel` e `verificar_disponibilidade` agora delegam a execução para o `AgendamentoService`.
    *   Redução significativa da complexidade da classe `Psicologo`.
*   **Refatoração de Views**:
    *   `PerfilView`: Lógica de agendamento movida para `ConsultaService`.

## 2. Segurança 🔐

Implementadas camadas de proteção para dados e infraestrutura.

*   **Rate Limiting**:
    *   Implementado `django-ratelimit` para prevenir ataques de força bruta.
    *   **Login**: Limitado a 5 tentativas/hora por IP.
    *   **Cadastro (Paciente/Psicólogo)**: Limitado a 3 tentativas/hora por IP.
*   **Gestão de Segredos**:
    *   Substituição de `SECRET_KEY` e `DEBUG` hardcoded por variáveis de ambiente usando `python-decouple`.
    *   Criação de `.env.example` para documentação.
*   **Hardening de Produção**:
    *   Configurações condicionais para SSL/HTTPS e Cookies Seguros quando `DEBUG=False`.

## 3. Performance ⚡

Otimizações para garantir escalabilidade e tempo de resposta.

*   **Índices de Banco de Dados**:
    *   Adicionados índices em `Consulta` (`data_hora_agendada`, `estado`, `paciente`, `psicologo`).
    *   Adicionado índice em `Psicologo` (`valor_consulta`).
    *   **Impacto**: Aceleração de queries de filtragem e ordenação.
*   **Otimização de Queries**:
    *   Resolução de problemas de N+1 em views críticas.

## 4. Confiabilidade e Correção de Bugs 🐛

Correções vitais para a estabilidade do sistema.

*   **Envio de E-mails**:
    *   Refatorado `Notificacao.save()` para garantir que o objeto seja salvo antes do envio do e-mail.
    *   Adicionado bloco `try/except` com logging para evitar que falhas no SMTP quebrem o fluxo da aplicação.
*   **Bug Crítico de Timezone (Resolvido)**:
    *   **Problema**: Falhas na verificação de disponibilidade quando servidor e cliente estavam em fusos diferentes.
    *   **Causa**: Comparação direta de `isoweekday()` e `time()` sem normalização.
    *   **Solução**: Implementada normalização para timezone local antes da verificação em `AgendamentoService` e `IntervaloDisponibilidade`.
*   **Validação de Consultas**:
    *   Restaurada lógica de validação em `Consulta.clean()` para impedir agendamentos em horários indisponíveis ou conflitantes.

## 5. Qualidade de Código e Testes ✅

Esforço intensivo para garantir a integridade do sistema.

*   **Correção de Testes**:
    *   **17 falhas de Timezone**: Resolvidas com a correção da lógica de normalização.
    *   **Falhas de Comparação (`test_from_matriz`)**: Corrigido método `tem_as_mesmas_datas_hora_que` para comparar datas em UTC.
    *   **Erro de Integridade**: Ajustados testes para não persistir dados duplicados desnecessariamente.
*   **Status Final**:
    *   **60 Testes Executados**.
    *   **0 Falhas**.
    *   **100% de Aprovação**.

---

**Conclusão**: O sistema encontra-se em estado estável, seguro e performático, pronto para as próximas etapas de desenvolvimento ou deploy.
