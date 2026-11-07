-- ==========================================================
-- V003: Modelagem de Profissionais de Saúde e Credenciais
-- Tabelas: perfis_profissionais, credenciais, disponibilidades
-- ==========================================================

CREATE TABLE IF NOT EXISTS perfis_profissionais (
    usuario_id INT PRIMARY KEY,
    categoria ENUM('cuidador', 'tecnico_enfermagem', 'enfermeiro') NOT NULL,
    registro_conselho VARCHAR(30) NULL,
    uf_conselho CHAR(2) NULL,
    valor_diaria_12h_centavos INT UNSIGNED NOT NULL DEFAULT 15000,
    valor_diaria_24h_centavos INT UNSIGNED NULL DEFAULT 28000,
    cidade VARCHAR(100) NOT NULL,
    uf CHAR(2) NOT NULL,
    raio_atendimento_km SMALLINT UNSIGNED NOT NULL DEFAULT 15,
    aceita_emergencial BOOLEAN NOT NULL DEFAULT FALSE,
    apresentacao TEXT NULL,
    status_verificacao ENUM('pendente', 'em_analise', 'aprovado', 'rejeitado', 'suspenso') NOT NULL DEFAULT 'pendente',
    verificado_por INT NULL,
    verificado_em DATETIME NULL,
    nota_media DECIMAL(3,2) NOT NULL DEFAULT 0.00,
    total_avaliacoes INT UNSIGNED NOT NULL DEFAULT 0,
    stripe_account_id VARCHAR(255) NULL,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NULL ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_pp_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    CONSTRAINT fk_pp_verificador FOREIGN KEY (verificado_por) REFERENCES usuarios(id) ON DELETE SET NULL,
    INDEX idx_pp_busca (status_verificacao, categoria, uf, cidade)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS credenciais (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    tipo ENUM('coren', 'diploma', 'antecedentes', 'documento_identidade', 'comprovante_endereco', 'certificado_curso', 'cnpj_alvara') NOT NULL,
    object_key VARCHAR(512) NOT NULL,
    mime VARCHAR(100) NOT NULL,
    tamanho_bytes INT UNSIGNED NOT NULL,
    status ENUM('pendente', 'aprovado', 'rejeitado') NOT NULL DEFAULT 'pendente',
    motivo_rejeicao VARCHAR(255) NULL,
    validade DATE NULL,
    revisado_por INT NULL,
    revisado_em DATETIME NULL,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    FOREIGN KEY (revisado_por) REFERENCES usuarios(id) ON DELETE SET NULL,
    INDEX idx_cred_fila (status, criado_em)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS disponibilidades (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    dia_semana TINYINT UNSIGNED NOT NULL, -- 0=Domingo, 1=Segunda, ..., 6=Sábado
    turno ENUM('diurno_12h', 'noturno_12h', 'plantao_24h') NOT NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    UNIQUE KEY uq_disp_turno (usuario_id, dia_semana, turno)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

