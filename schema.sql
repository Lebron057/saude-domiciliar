-- ==========================================================
-- Esquema Consolidado de Referência — CuidaHome (MariaDB 11.8)
-- NOTA: A fonte da verdade para aplicação no banco são as
-- migrações versionadas em: db/migrations/V*.sql
-- ==========================================================

-- 1. Usuários e Papéis (RBAC)
CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    telefone VARCHAR(20) NULL,
    cidade VARCHAR(100) NULL,
    uf CHAR(2) NULL,
    senha_hash VARCHAR(255) NOT NULL,
    role VARCHAR(32) NOT NULL DEFAULT 'familiar_paciente',
    bio TEXT NULL,
    avatar_key VARCHAR(512) NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    stripe_customer_id VARCHAR(255) NULL,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_usuarios_role (role),
    INDEX idx_usuarios_cidade_uf (uf, cidade)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Tokens de Recuperação de Senha
CREATE TABLE IF NOT EXISTS reset_tokens (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    token VARCHAR(255) UNIQUE NOT NULL,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expira_em DATETIME NOT NULL,
    usado BOOLEAN NOT NULL DEFAULT FALSE,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. Perfil Profissional de Saúde
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
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    FOREIGN KEY (verificado_por) REFERENCES usuarios(id) ON DELETE SET NULL,
    INDEX idx_pp_busca (status_verificacao, categoria, uf, cidade)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. Credenciais e Documentos do Profissional
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

-- 5. Disponibilidade do Profissional
CREATE TABLE IF NOT EXISTS disponibilidades (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    dia_semana TINYINT UNSIGNED NOT NULL,
    turno ENUM('diurno_12h', 'noturno_12h', 'plantao_24h') NOT NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    UNIQUE KEY uq_disp_turno (usuario_id, dia_semana, turno)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. Pacientes Dependentes
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
    FOREIGN KEY (familiar_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    INDEX idx_paciente_familiar (familiar_id, ativo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. Plantões Assistenciais
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
    FOREIGN KEY (familiar_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    FOREIGN KEY (paciente_id) REFERENCES pacientes(id) ON DELETE CASCADE,
    FOREIGN KEY (profissional_id) REFERENCES usuarios(id) ON DELETE SET NULL,
    INDEX idx_pl_mural (status, urgencia, uf, cidade, inicio),
    INDEX idx_pl_agenda (profissional_id, inicio),
    INDEX idx_pl_familiar (familiar_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. Candidaturas de Profissionais no Mural
CREATE TABLE IF NOT EXISTS candidaturas_plantao (
    id INT AUTO_INCREMENT PRIMARY KEY,
    plantao_id INT NOT NULL,
    profissional_id INT NOT NULL,
    status ENUM('pendente', 'aceito', 'recusado') NOT NULL DEFAULT 'pendente',
    mensagem VARCHAR(255) NULL,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (plantao_id) REFERENCES plantoes(id) ON DELETE CASCADE,
    FOREIGN KEY (profissional_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    UNIQUE KEY uq_candidatura (plantao_id, profissional_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 9. Avaliações
CREATE TABLE IF NOT EXISTS avaliacoes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    plantao_id INT NOT NULL UNIQUE,
    avaliador_id INT NOT NULL,
    avaliado_id INT NOT NULL,
    nota TINYINT UNSIGNED NOT NULL,
    comentario TEXT NULL,
    resposta TEXT NULL,
    status_moderacao ENUM('publicado', 'oculto', 'em_analise') NOT NULL DEFAULT 'publicado',
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (plantao_id) REFERENCES plantoes(id) ON DELETE CASCADE,
    FOREIGN KEY (avaliador_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    FOREIGN KEY (avaliado_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    INDEX idx_aval_profissional (avaliado_id, status_moderacao)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 10. Ledger de Repasses Financeiros
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
    FOREIGN KEY (beneficiario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    UNIQUE KEY uq_repasse_origem (origem_tipo, origem_id, beneficiario_id),
    INDEX idx_repasse_status (beneficiario_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 11. Categorias de Equipamento
CREATE TABLE IF NOT EXISTS categorias_equipamento (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL UNIQUE,
    slug VARCHAR(100) NOT NULL UNIQUE,
    descricao TEXT NULL,
    icone VARCHAR(50) NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 12. Equipamentos do Catálogo
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
    FOREIGN KEY (fornecedor_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    FOREIGN KEY (categoria_id) REFERENCES categorias_equipamento(id),
    INDEX idx_eq_catalogo (ativo, categoria_id, preco_mensal_centavos)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 13. Fotos de Equipamentos
CREATE TABLE IF NOT EXISTS fotos_equipamento (
    id INT AUTO_INCREMENT PRIMARY KEY,
    equipamento_id INT NOT NULL,
    object_key VARCHAR(512) NOT NULL,
    ordem TINYINT UNSIGNED NOT NULL DEFAULT 0,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (equipamento_id) REFERENCES equipamentos(id) ON DELETE CASCADE,
    INDEX idx_foto_eq (equipamento_id, ordem)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 14. Unidades Físicas (Patrimônio/Estoque)
CREATE TABLE IF NOT EXISTS unidades_equipamento (
    id INT AUTO_INCREMENT PRIMARY KEY,
    equipamento_id INT NOT NULL,
    numero_patrimonio VARCHAR(100) NOT NULL,
    numero_serie VARCHAR(100) NULL,
    status ENUM('disponivel', 'locado', 'em_manutencao', 'baixado') NOT NULL DEFAULT 'disponivel',
    observacoes_estado TEXT NULL,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (equipamento_id) REFERENCES equipamentos(id) ON DELETE CASCADE,
    UNIQUE KEY uq_patrimonio (equipamento_id, numero_patrimonio),
    INDEX idx_unid_status (equipamento_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 15. Locações e Assinaturas
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
    FOREIGN KEY (cliente_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    FOREIGN KEY (paciente_id) REFERENCES pacientes(id) ON DELETE SET NULL,
    FOREIGN KEY (equipamento_id) REFERENCES equipamentos(id),
    FOREIGN KEY (unidade_id) REFERENCES unidades_equipamento(id) ON DELETE SET NULL,
    UNIQUE KEY uq_loc_subscription (stripe_subscription_id),
    INDEX idx_loc_cliente (cliente_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 16. Cauções
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
    FOREIGN KEY (locacao_id) REFERENCES locacoes(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 17. Documentos (Laudos, Termos, Vistorias)
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
    FOREIGN KEY (paciente_id) REFERENCES pacientes(id) ON DELETE CASCADE,
    FOREIGN KEY (locacao_id) REFERENCES locacoes(id) ON DELETE SET NULL,
    FOREIGN KEY (criado_por) REFERENCES usuarios(id) ON DELETE CASCADE,
    INDEX idx_doc_paciente (paciente_id),
    INDEX idx_doc_locacao (locacao_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 18. Movimentações Logísticas
CREATE TABLE IF NOT EXISTS movimentacoes_locacao (
    id INT AUTO_INCREMENT PRIMARY KEY,
    locacao_id INT NOT NULL,
    responsavel_id INT NOT NULL,
    tipo ENUM('despacho', 'entrega', 'solicitacao_devolucao', 'recolhimento', 'vistoria') NOT NULL,
    observacoes TEXT NULL,
    foto_vistoria_key VARCHAR(512) NULL,
    registrado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (locacao_id) REFERENCES locacoes(id) ON DELETE CASCADE,
    FOREIGN KEY (responsavel_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    INDEX idx_mov_locacao (locacao_id, registrado_em)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 19. Contratos e Termos de Aceite Digital
CREATE TABLE IF NOT EXISTS contratos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    tipo ENUM('locacao_equipamento', 'intermediacao_plantao', 'prestacao_servico') NOT NULL,
    referencia_id INT NOT NULL,
    versao_termo VARCHAR(20) NOT NULL DEFAULT 'v1.0',
    ip_aceite VARCHAR(45) NULL,
    aceito_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    INDEX idx_contrato_ref (tipo, referencia_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 20. Idempotência de Webhooks Stripe
CREATE TABLE IF NOT EXISTS stripe_eventos (
    event_id VARCHAR(255) PRIMARY KEY,
    tipo VARCHAR(100) NOT NULL,
    recebido_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processado_em DATETIME NULL,
    status ENUM('processado', 'ignorado', 'erro') NOT NULL DEFAULT 'processado',
    erro TEXT NULL,
    INDEX idx_stripe_evt_tipo (tipo, recebido_em)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 21. Favoritos Polimórficos
CREATE TABLE IF NOT EXISTS favoritos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    alvo_tipo ENUM('profissional', 'equipamento') NOT NULL,
    alvo_id INT NOT NULL,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    UNIQUE KEY uq_fav_alvo (usuario_id, alvo_tipo, alvo_id),
    INDEX idx_fav_alvo (alvo_tipo, alvo_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
