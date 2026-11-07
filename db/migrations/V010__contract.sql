-- ==========================================================
-- V010: Fase de Contração (Contract / Destrutiva)
-- ATENÇÃO: Esta migração é irreversível!
-- Deve ser executada manualmente via:
--     python -m db.migrate --allow-contract
-- após a validação completa e estabilização em produção.
-- ==========================================================

DROP TABLE IF EXISTS legacy_favoritos_filmes;
DROP TABLE IF EXISTS legacy_comentarios_filmes;

ALTER TABLE usuarios
    DROP COLUMN IF EXISTS premium,
    DROP COLUMN IF EXISTS stripe_subscription_id;

-- Adiciona constraint de validação estrita dos papéis válidos
ALTER TABLE usuarios
    ADD CONSTRAINT chk_usuarios_role CHECK (role IN ('admin', 'profissional_saude', 'familiar_paciente', 'fornecedor_equipamento'));

