-- ==========================================================
-- V008: Idempotência de Webhooks Stripe e Seeds Iniciais
-- ==========================================================

CREATE TABLE IF NOT EXISTS stripe_eventos (
    event_id VARCHAR(255) PRIMARY KEY,
    tipo VARCHAR(100) NOT NULL,
    recebido_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processado_em DATETIME NULL,
    status ENUM('processado', 'ignorado', 'erro') NOT NULL DEFAULT 'processado',
    erro TEXT NULL,
    INDEX idx_stripe_evt_tipo (tipo, recebido_em)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Seeds das categorias fundamentais de equipamentos ortopédicos
INSERT IGNORE INTO categorias_equipamento (nome, slug, descricao, icone) VALUES
('Cadeiras de Rodas', 'cadeiras-de-rodas', 'Cadeiras de rodas manuais, motorizadas e de banho.', 'fa-wheelchair'),
('Camas Hospitalares', 'camas-hospitalares', 'Camas articuladas manuais e elétricas, com colchão especial.', 'fa-bed'),
('Andadores e Muletas', 'andadores-muletas', 'Andadores articulados, fixos e pares de muletas axilares ou canadenses.', 'fa-crutch'),
('Suporte e Conforto', 'suporte-conforto', 'Suportes de soro, colchões caixa de ovo e aspiradores cirúrgicos.', 'fa-heartbeat');

