-- ==========================================================
-- V009: Arquivamento Probatório das Tabelas de Filmes
-- 1. Preserva o histórico da P1 renomeando favoritos e comentários.
-- 2. Cria nova tabela polimórfica de favoritos para o domínio de Saúde.
-- ==========================================================

RENAME TABLE favoritos TO legacy_favoritos_filmes,
             comentarios TO legacy_comentarios_filmes;

CREATE TABLE IF NOT EXISTS favoritos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    alvo_tipo ENUM('profissional', 'equipamento') NOT NULL,
    alvo_id INT NOT NULL,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_fav_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    UNIQUE KEY uq_fav_alvo (usuario_id, alvo_tipo, alvo_id),
    INDEX idx_fav_alvo (alvo_tipo, alvo_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

