-- ==========================================================
-- V005: Modelagem do Ciclo de Plantões, Avaliações e Repasses
-- Tabelas: plantoes, candidaturas_plantao, avaliacoes, repasses
-- ==========================================================

CREATE TABLE IF NOT EXISTS plantoes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    familiar_id INT NOT NULL,
    paciente_id INT NOT NULL,
    profissional_id INT NULL,
    modalidade ENUM('direto', 'mural') NOT NULL DEFAULT 'direto',
    urgencia ENUM('agendado', 'emergencial') NOT NULL DEFAULT 'agendado',
    categoria_exigida ENUM('cuidador', 'tecnico_enfermagem', 'enfermeiro') NOT NULL,
    inicio DATETIME NOT NULL,
    fim DATETIME NOT NULL,
    endereco_atendimento VARCHAR(255) NOT NULL,
    cidade VARCHAR(100) NOT NULL,
    uf CHAR(2) NOT NULL,
    valor_diaria_centavos INT UNSIGNED NOT NULL,
    taxa_percentual DECIMAL(5,2) NOT NULL DEFAULT 12.00,
    taxa_centavos INT UNSIGNED NOT NULL,
    valor_repasse_centavos INT UNSIGNED NOT NULL,
    status ENUM('aberto', 'solicitado', 'aceito', 'aguardando_pagamento', 'confirmado', 'em_andamento', 'concluido', 'cancelado', 'expirado') NOT NULL DEFAULT 'solicitado',
    stripe_checkout_session_id VARCHAR(255) NULL,
    stripe_payment_intent_id VARCHAR(255) NULL,
    observacoes TEXT NULL,
    aceito_em DATETIME NULL,
    checkin_em DATETIME NULL,
    checkout_em DATETIME NULL,
    cancelado_em DATETIME NULL,
    motivo_cancelamento VARCHAR(255) NULL,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NULL ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_pl_familiar FOREIGN KEY (familiar_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    CONSTRAINT fk_pl_paciente FOREIGN KEY (paciente_id) REFERENCES pacientes(id) ON DELETE CASCADE,
    CONSTRAINT fk_pl_prof FOREIGN KEY (profissional_id) REFERENCES usuarios(id) ON DELETE SET NULL,
    CONSTRAINT chk_pl_periodo CHECK (fim > inicio),
    INDEX idx_pl_mural (status, urgencia, uf, cidade, inicio),
    INDEX idx_pl_agenda (profissional_id, inicio),
    INDEX idx_pl_familiar (familiar_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS candidaturas_plantao (
    id INT AUTO_INCREMENT PRIMARY KEY,
    plantao_id INT NOT NULL,
    profissional_id INT NOT NULL,
    status ENUM('pendente', 'aceito', 'recusado') NOT NULL DEFAULT 'pendente',
    mensagem VARCHAR(255) NULL,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_cand_plantao FOREIGN KEY (plantao_id) REFERENCES plantoes(id) ON DELETE CASCADE,
    CONSTRAINT fk_cand_profissional FOREIGN KEY (profissional_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    UNIQUE KEY uq_candidatura (plantao_id, profissional_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS avaliacoes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    plantao_id INT NOT NULL UNIQUE,
    avaliador_id INT NOT NULL,
    avaliado_id INT NOT NULL,
    nota TINYINT UNSIGNED NOT NULL, -- 1 a 5
    comentario TEXT NULL,
    resposta TEXT NULL,
    status_moderacao ENUM('publicado', 'oculto', 'em_analise') NOT NULL DEFAULT 'publicado',
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_aval_plantao FOREIGN KEY (plantao_id) REFERENCES plantoes(id) ON DELETE CASCADE,
    CONSTRAINT fk_aval_avaliador FOREIGN KEY (avaliador_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    CONSTRAINT fk_aval_avaliado FOREIGN KEY (avaliado_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    CONSTRAINT chk_aval_nota CHECK (nota >= 1 AND nota <= 5),
    INDEX idx_aval_profissional (avaliado_id, status_moderacao)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS repasses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    beneficiario_id INT NOT NULL,
    origem_tipo ENUM('plantao', 'fatura_locacao') NOT NULL,
    origem_id INT NOT NULL,
    valor_bruto_centavos INT UNSIGNED NOT NULL,
    taxa_plataforma_centavos INT UNSIGNED NOT NULL,
    valor_liquido_centavos INT UNSIGNED NOT NULL,
    status ENUM('pendente', 'liberado', 'pago', 'estornado') NOT NULL DEFAULT 'pendente',
    stripe_transfer_id VARCHAR(255) NULL,
    pago_em DATETIME NULL,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NULL ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_repasse_beneficiario FOREIGN KEY (beneficiario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    UNIQUE KEY uq_repasse_origem (origem_tipo, origem_id, beneficiario_id),
    INDEX idx_repasse_status (beneficiario_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

