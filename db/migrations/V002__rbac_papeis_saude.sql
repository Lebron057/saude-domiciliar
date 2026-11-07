-- ==========================================================
-- V002: RBAC — Expansão de Papéis e Perfil de Usuário
-- 1. Amplia role para VARCHAR(32) para comportar novos papéis.
-- 2. Converte role legada 'user' para 'familiar_paciente'.
-- 3. Adiciona campos de contato e localidade.
-- ==========================================================

ALTER TABLE usuarios MODIFY role VARCHAR(32) NOT NULL DEFAULT 'familiar_paciente';

UPDATE usuarios SET role = 'familiar_paciente' WHERE role = 'user';

ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS telefone VARCHAR(20) NULL AFTER email,
    ADD COLUMN IF NOT EXISTS cidade VARCHAR(100) NULL AFTER telefone,
    ADD COLUMN IF NOT EXISTS uf CHAR(2) NULL AFTER cidade,
    ADD COLUMN IF NOT EXISTS ativo BOOLEAN NOT NULL DEFAULT TRUE AFTER avatar_key,
    ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP;

CREATE INDEX IF NOT EXISTS idx_usuarios_role ON usuarios(role);
CREATE INDEX IF NOT EXISTS idx_usuarios_cidade_uf ON usuarios(uf, cidade);

