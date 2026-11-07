-- ==========================================================
-- V004: Modelagem de Pacientes e Documentos Médicos Sensíveis
-- Tabelas: pacientes, documentos
-- ==========================================================

CREATE TABLE IF NOT EXISTS pacientes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    familiar_id INT NOT NULL,
    nome VARCHAR(120) NOT NULL,
    data_nascimento DATE NULL,
    cidade VARCHAR(100) NOT NULL,
    uf CHAR(2) NOT NULL,
    condicao_resumo TEXT NULL,
    mobilidade ENUM('independente', 'mobilidade_reduzida', 'cadeirante', 'acamado') NOT NULL DEFAULT 'mobilidade_reduzida',
    alergias_restricoes TEXT NULL,
    contato_emergencia VARCHAR(100) NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NULL ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_paciente_familiar FOREIGN KEY (familiar_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    INDEX idx_paciente_familiar (familiar_id, ativo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS documentos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    paciente_id INT NULL,
    locacao_id INT NULL,
    criado_por INT NOT NULL,
    tipo ENUM('laudo_medico', 'receita', 'termo_locacao', 'termo_plantao', 'vistoria_entrega', 'vistoria_devolucao') NOT NULL,
    object_key VARCHAR(512) NOT NULL,
    mime VARCHAR(100) NOT NULL,
    tamanho_bytes INT UNSIGNED NOT NULL,
    descricao VARCHAR(255) NULL,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_doc_paciente FOREIGN KEY (paciente_id) REFERENCES pacientes(id) ON DELETE CASCADE,
    CONSTRAINT fk_doc_criador FOREIGN KEY (criado_por) REFERENCES usuarios(id) ON DELETE CASCADE,
    INDEX idx_doc_paciente (paciente_id),
    INDEX idx_doc_locacao (locacao_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

