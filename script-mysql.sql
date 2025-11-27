DROP DATABASE IF EXISTS db_test_easy_talk;
CREATE DATABASE IF NOT EXISTS db_test_easy_talk;
USE db_test_easy_talk;

SET default_storage_engine = INNODB;
SET NAMES utf8mb4;
SET SESSION sql_mode = 'STRICT_TRANS_TABLES';


CREATE TABLE IF NOT EXISTS tb_auth_group
(
    id   INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL UNIQUE
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;


CREATE TABLE IF NOT EXISTS tb_auth_permission
(
    id       INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name     VARCHAR(255) NOT NULL,
    codename VARCHAR(100) NOT NULL,
    UNIQUE KEY tb_auth_permission_codename_uk (codename)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;


CREATE TABLE IF NOT EXISTS tb_usuario
(
    id           INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    password     VARCHAR(128) NOT NULL,
    last_login   DATETIME(6)  NULL,
    is_superuser TINYINT UNSIGNED NOT NULL DEFAULT 0,
    email        VARCHAR(254) NOT NULL,
    is_active    TINYINT UNSIGNED NOT NULL DEFAULT 1,
    is_staff     TINYINT UNSIGNED NOT NULL DEFAULT 0,
    UNIQUE KEY tb_usuario_email_uk (email)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;


CREATE TABLE IF NOT EXISTS tb_usuario_groups
(
    id         INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT UNSIGNED NOT NULL,
    group_id   INT UNSIGNED NOT NULL,
    UNIQUE KEY tb_usuario_groups_usuario_group_uk (usuario_id, group_id),
    CONSTRAINT tb_usuario_groups_usuario_fk
        FOREIGN KEY (usuario_id)
            REFERENCES tb_usuario (id)
            ON DELETE CASCADE,
    CONSTRAINT tb_usuario_groups_group_fk
        FOREIGN KEY (group_id)
            REFERENCES tb_auth_group (id)
            ON DELETE CASCADE
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;


CREATE TABLE IF NOT EXISTS tb_usuario_user_permissions
(
    id            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    usuario_id    INT UNSIGNED NOT NULL,
    permission_id INT UNSIGNED NOT NULL,
    UNIQUE KEY tb_usuario_user_permissions_usuario_perm_uk (usuario_id, permission_id),
    CONSTRAINT tb_usuario_user_permissions_usuario_fk
        FOREIGN KEY (usuario_id)
            REFERENCES tb_usuario (id)
            ON DELETE CASCADE,
    CONSTRAINT tb_usuario_user_permissions_permission_fk
        FOREIGN KEY (permission_id)
            REFERENCES tb_auth_permission (id)
            ON DELETE CASCADE
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;


CREATE TABLE IF NOT EXISTS tb_especializacao
(
    id        INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    titulo    VARCHAR(50) NOT NULL,
    descricao LONGTEXT    NOT NULL,
    UNIQUE KEY tb_especializacao_titulo_uk (titulo)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;


CREATE TABLE IF NOT EXISTS tb_paciente
(
    id         INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT UNSIGNED  NOT NULL,
    nome       VARCHAR(50)   NOT NULL,
    cpf        VARCHAR(14)   NOT NULL,
    foto       VARCHAR(100)  NULL,
    UNIQUE KEY tb_paciente_cpf_uk (cpf),
    UNIQUE KEY tb_paciente_usuario_uk (usuario_id),
    CONSTRAINT tb_paciente_usuario_fk
        FOREIGN KEY (usuario_id)
            REFERENCES tb_usuario (id)
            ON DELETE CASCADE
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;


CREATE TABLE IF NOT EXISTS tb_psicologo
(
    id             INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    usuario_id     INT UNSIGNED      NOT NULL,
    nome_completo  VARCHAR(50)       NOT NULL,
    crp            VARCHAR(20)       NOT NULL,
    foto           VARCHAR(100)      NULL,
    sobre_mim      LONGTEXT          NULL,
    valor_consulta DECIMAL(10, 2) UNSIGNED NULL,
    UNIQUE KEY tb_psicologo_usuario_uk (usuario_id),
    UNIQUE KEY tb_psicologo_crp_uk (crp),
    CONSTRAINT tb_psicologo_usuario_fk
        FOREIGN KEY (usuario_id)
            REFERENCES tb_usuario (id)
            ON DELETE CASCADE
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;


CREATE TABLE IF NOT EXISTS tb_psicologo_especializacoes
(
    id                INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    psicologo_id      INT UNSIGNED NOT NULL,
    especializacao_id INT UNSIGNED NOT NULL,
    UNIQUE KEY tb_psicologo_especializacao_uk (psicologo_id, especializacao_id),
    CONSTRAINT tb_psicologo_especializacoes_psicologo_fk
        FOREIGN KEY (psicologo_id)
            REFERENCES tb_psicologo (id)
            ON DELETE CASCADE,
    CONSTRAINT tb_psicologo_especializacoes_especializacao_fk
        FOREIGN KEY (especializacao_id)
            REFERENCES tb_especializacao (id)
            ON DELETE CASCADE
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;


CREATE TABLE IF NOT EXISTS tb_intervalo_disponibilidade
(
    id               INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    data_hora_inicio DATETIME(6) NOT NULL,
    data_hora_fim    DATETIME(6) NOT NULL,
    psicologo_id     INT UNSIGNED NOT NULL,
    CONSTRAINT tb_intervalo_disponibilidade_psicologo_fk
        FOREIGN KEY (psicologo_id)
            REFERENCES tb_psicologo (id)
            ON DELETE CASCADE,
    INDEX tb_intervalo_disponibilidade_psicologo_dhi_idx (psicologo_id, data_hora_inicio)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;


CREATE TABLE IF NOT EXISTS tb_consulta
(
    id                   INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    data_hora_solicitada DATETIME(6)       NOT NULL,
    data_hora_agendada   DATETIME(6)       NOT NULL,
    duracao              BIGINT UNSIGNED   NULL,
    estado               VARCHAR(20)       NOT NULL DEFAULT 'SOLICITADA',
    anotacoes            LONGTEXT          NULL,
    checklist_tarefas    LONGTEXT          NULL,
    paciente_id          INT UNSIGNED      NOT NULL,
    psicologo_id         INT UNSIGNED      NOT NULL,
    jitsi_room           VARCHAR(128)      NULL,
    CONSTRAINT tb_consulta_paciente_fk
        FOREIGN KEY (paciente_id)
            REFERENCES tb_paciente (id)
            ON DELETE CASCADE,
    CONSTRAINT tb_consulta_psicologo_fk
        FOREIGN KEY (psicologo_id)
            REFERENCES tb_psicologo (id)
            ON DELETE CASCADE,
    INDEX tb_consulta_estado_dh_idx    (estado,      data_hora_agendada),
    INDEX tb_consulta_paciente_dh_idx  (paciente_id, data_hora_agendada),
    INDEX tb_consulta_psicologo_dh_idx (psicologo_id, data_hora_agendada)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;


CREATE TABLE IF NOT EXISTS tb_notificacao
(
    id               INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tipo             VARCHAR(50)      NOT NULL,
    lida             TINYINT UNSIGNED NOT NULL DEFAULT 0,
    data_hora_criada DATETIME(6)      NOT NULL,
    remetente_id     INT UNSIGNED     NULL,
    destinatario_id  INT UNSIGNED     NOT NULL,
    consulta_id      INT UNSIGNED     NOT NULL,
    CONSTRAINT tb_notificacao_remetente_fk
        FOREIGN KEY (remetente_id)
            REFERENCES tb_usuario (id)
            ON DELETE CASCADE,
    CONSTRAINT tb_notificacao_destinatario_fk
        FOREIGN KEY (destinatario_id)
            REFERENCES tb_usuario (id)
            ON DELETE CASCADE,
    CONSTRAINT tb_notificacao_consulta_fk
        FOREIGN KEY (consulta_id)
            REFERENCES tb_consulta (id)
            ON DELETE CASCADE,
    INDEX tb_notificacao_destinatario_lida_idx (destinatario_id, lida),
    INDEX tb_notificacao_consulta_idx          (consulta_id)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;
