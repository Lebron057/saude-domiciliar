-- ==========================================================
-- V006: Catálogo de Equipamentos Ortopédicos e Hospitalares
-- Tabelas: categorias_equipamento, equipamentos, fotos_equipamento, unidades_equipamento
-- ==========================================================

CREATE TABLE IF NOT EXISTS categorias_equipamento (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL UNIQUE,
    slug VARCHAR(100) NOT NULL UNIQUE,
    descricao TEXT NULL,
    icone VARCHAR(50) NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS equipamentos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    fornecedor_id INT NOT NULL,
    categoria_id INT NOT NULL,
    nome VARCHAR(150) NOT NULL,
    descricao TEXT NULL,
    especificacoes JSON NULL,
    preco_mensal_centavos INT UNSIGNED NOT NULL,
    valor_caucao_centavos INT UNSIGNED NOT NULL,
    stripe_product_id VARCHAR(255) NULL,
    stripe_price_id VARCHAR(255) NULL,
    foto_principal_key VARCHAR(512) NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NULL ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_eq_fornecedor FOREIGN KEY (fornecedor_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    CONSTRAINT fk_eq_categoria FOREIGN KEY (categoria_id) REFERENCES categorias_equipamento(id),
    INDEX idx_eq_catalogo (ativo, categoria_id, preco_mensal_centavos)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS fotos_equipamento (
    id INT AUTO_INCREMENT PRIMARY KEY,
    equipamento_id INT NOT NULL,
    object_key VARCHAR(512) NOT NULL,
    ordem TINYINT UNSIGNED NOT NULL DEFAULT 0,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_foto_equipamento FOREIGN KEY (equipamento_id) REFERENCES equipamentos(id) ON DELETE CASCADE,
    INDEX idx_foto_eq (equipamento_id, ordem)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS unidades_equipamento (
    id INT AUTO_INCREMENT PRIMARY KEY,
    equipamento_id INT NOT NULL,
    numero_patrimonio VARCHAR(100) NOT NULL,
    numero_serie VARCHAR(100) NULL,
    status ENUM('disponivel', 'locado', 'em_manutencao', 'baixado') NOT NULL DEFAULT 'disponivel',
    observacoes_estado TEXT NULL,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_unid_equipamento FOREIGN KEY (equipamento_id) REFERENCES equipamentos(id) ON DELETE CASCADE,
    UNIQUE KEY uq_patrimonio (equipamento_id, numero_patrimonio),
    INDEX idx_unid_status (equipamento_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

