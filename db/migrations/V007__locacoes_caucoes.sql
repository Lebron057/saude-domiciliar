-- ==========================================================
-- V007: Locações, Cauções e Rastreamento Logístico
-- Tabelas: locacoes, caucoes, movimentacoes_locacao, contratos
-- ==========================================================

CREATE TABLE IF NOT EXISTS locacoes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cliente_id INT NOT NULL,
    paciente_id INT NULL,
    equipamento_id INT NOT NULL,
    unidade_id INT NULL,
    endereco_entrega VARCHAR(255) NOT NULL,
    cidade VARCHAR(100) NOT NULL,
    uf CHAR(2) NOT NULL,
    data_entrega_prevista DATE NOT NULL,
    periodo_previsto_dias SMALLINT UNSIGNED NOT NULL DEFAULT 30,
    status ENUM('pendente_pagamento', 'pendente_caucao', 'em_separacao', 'despachada', 'entregue', 'devolucao_solicitada', 'recolhida', 'encerrada', 'cancelada', 'inadimplente') NOT NULL DEFAULT 'pendente_pagamento',
    stripe_checkout_session_id VARCHAR(255) NULL,
    stripe_subscription_id VARCHAR(255) NULL,
    stripe_customer_id VARCHAR(255) NULL,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NULL ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_loc_cliente FOREIGN KEY (cliente_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    CONSTRAINT fk_loc_paciente FOREIGN KEY (paciente_id) REFERENCES pacientes(id) ON DELETE SET NULL,
    CONSTRAINT fk_loc_equipamento FOREIGN KEY (equipamento_id) REFERENCES equipamentos(id),
    CONSTRAINT fk_loc_unidade FOREIGN KEY (unidade_id) REFERENCES unidades_equipamento(id) ON DELETE SET NULL,
    UNIQUE KEY uq_loc_subscription (stripe_subscription_id),
    INDEX idx_loc_cliente (cliente_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS caucoes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    locacao_id INT NOT NULL UNIQUE,
    valor_centavos INT UNSIGNED NOT NULL,
    stripe_payment_intent_id VARCHAR(255) NULL UNIQUE,
    status ENUM('pendente', 'autorizada', 'capturada_parcial', 'capturada', 'liberada', 'expirada', 'falhou') NOT NULL DEFAULT 'pendente',
    capture_before DATETIME NULL,
    capturado_centavos INT UNSIGNED NOT NULL DEFAULT 0,
    motivo VARCHAR(255) NULL,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NULL ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_caucao_locacao FOREIGN KEY (locacao_id) REFERENCES locacoes(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS movimentacoes_locacao (
    id INT AUTO_INCREMENT PRIMARY KEY,
    locacao_id INT NOT NULL,
    responsavel_id INT NOT NULL,
    tipo ENUM('despacho', 'entrega', 'solicitacao_devolucao', 'recolhimento', 'vistoria') NOT NULL,
    observacoes TEXT NULL,
    foto_vistoria_key VARCHAR(512) NULL,
    registrado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_mov_locacao FOREIGN KEY (locacao_id) REFERENCES locacoes(id) ON DELETE CASCADE,
    CONSTRAINT fk_mov_responsavel FOREIGN KEY (responsavel_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    INDEX idx_mov_locacao (locacao_id, registrado_em)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS contratos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    tipo ENUM('locacao_equipamento', 'intermediacao_plantao', 'prestacao_servico') NOT NULL,
    referencia_id INT NOT NULL, -- ID de locacoes ou plantoes
    versao_termo VARCHAR(20) NOT NULL DEFAULT 'v1.0',
    ip_aceite VARCHAR(45) NULL,
    aceito_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_contrato_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    INDEX idx_contrato_ref (tipo, referencia_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Adiciona constraint para integridade referencial em documentos(locacao_id)
ALTER TABLE documentos
    ADD CONSTRAINT fk_doc_locacao FOREIGN KEY (locacao_id) REFERENCES locacoes(id) ON DELETE SET NULL;

