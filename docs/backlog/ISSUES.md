# Backlog de Execução em Issues do GitHub — CuidaHome (`saude-domiciliar`)

> **Como usar:** Copie o conteúdo de cada issue abaixo diretamente para o campo de criação de issues no repositório `https://github.com/Lebron057/saude-domiciliar/issues/new`.
>
> Foram modeladas **12 issues** (o enunciado pedia entre 5 e 8), cobrindo todo o ciclo: da migração e saneamento (Fase 0/1) à entrega dos painéis e estabilização (Fase 7), além do template pronto para a **Issue de Entrega da Atividade 9**.

---

## Índice das Issues

- [Issue #1 — docs: estruturar novo README.md com modelo de negócio e mapa de migração](#issue-1--docs-estruturar-novo-readmemd-com-modelo-de-negócio-e-mapa-de-migração)
- [Issue #2 — chore(infra): sanear docker-compose, variáveis de ambiente e expurgar dependências legadas do TMDB](#issue-2--choreinfra-sanear-docker-compose-variáveis-de-ambiente-e-expurgar-dependências-legadas-do-tmdb)
- [Issue #3 — feat(db): implementar runner de migrations versionadas e idempotentes (expand/contract)](#issue-3--featdb-implementar-runner-de-migrations-versionadas-e-idempotentes-expandcontract)
- [Issue #4 — feat(db): modelar tabelas de plantões, locações, credenciais e arquivar schema de filmes](#issue-4--featdb-modelar-tabelas-de-plantões-locações-credenciais-e-arquivar-schema-de-filmes)
- [Issue #5 — feat(auth): expandir RBAC com 4 novos papéis, atributos complementares e autocadastro qualificado](#issue-5--featauth-expandir-rbac-com-4-novos-papéis-atributos-complementares-e-autocadastro-qualificado)
- [Issue #6 — feat(storage): reestruturar S3/Garage em 4 buckets com proxy autenticado para credenciais e laudos](#issue-6--featstorage-reestruturar-s3garage-em-4-buckets-com-proxy-autenticado-para-credenciais-e-laudos)
- [Issue #7 — feat(plantoes): implementar ciclo de contratação de plantões (direto e mural) com ledger de repasses](#issue-7--featplantoes-implementar-ciclo-de-contratação-de-plantões-direto-e-mural-com-ledger-de-repasses)
- [Issue #8 — feat(locacoes): implementar locação de equipamentos com Stripe Billing recorrente e caução](#issue-8--featlocacoes-implementar-locação-de-equipamentos-com-stripe-billing-recorrente-e-caução)
- [Issue #9 — feat(events): estruturar trilha de eventos de negócio no Redis Streams e métricas de auditoria](#issue-9--featevents-estruturar-trilha-de-eventos-de-negócio-no-redis-streams-e-métricas-de-auditoria)
- [Issue #10 — feat(ui): implementar Landing Page, Catálogo de Equipamentos e Mural de Profissionais](#issue-10--featui-implementar-landing-page-catálogo-de-equipamentos-e-mural-de-profissionais)
- [Issue #11 — feat(ui): implementar painéis dedicados (Familiar, Profissional, Fornecedor e Admin)](#issue-11--featui-implementar-painéis-dedicados-familiar-profissional-fornecedor-e-admin)
- [Issue #12 — ops: documentar e executar o runbook de deploy contínuo no Portainer e validação em produção](#issue-12--ops-documentar-e-executar-o-runbook-de-deploy-contínuo-no-portainer-e-validação-em-produção)
- [Template Extra: Issue de Entrega da Atividade 9](#template-extra-issue-de-entrega-da-atividade-9-menção-siriani)

---

### Issue #1 — `docs: estruturar novo README.md com modelo de negócio e mapa de migração`

**Título da Issue:**
```
docs: estruturar novo README.md com modelo de negócio e mapa de migração
```

**Descrição e Contexto:**
Adequar a documentação principal do repositório `saude-domiciliar` substituindo completamente o tema antigo de Catálogo de Filmes do Tom Hanks pelas diretrizes do novo produto **CuidaHome (Saúde & Atendimento Domiciliar)**, respeitando estritamente a ordem de 9 seções exigida na Atividade 9 e adicionando menção ao docente `@siriani`. Os arquivos de documentação antigos da P1 devem ser preservados em `docs/legado/` para histórico.

**Labels sugeridas:** `documentation`, `fase-0`

**Tarefas / Checklist de Implementação:**
- [ ] Mover `DOCUMENTACAO.md`, `catalogo-filmes-tom-hanks-spec.md` e `catalog_live.html` para `docs/legado/`.
- [ ] Criar novo `README.md` com as 9 seções na ordem exata:
  - [ ] 1. Nome do produto (*CuidaHome*) e Frase de impacto.
  - [ ] 2. A Dor (quem sofre, quando, quanto custa hoje, como resolvem hoje).
  - [ ] 3. Persona detalhada (*Mariana Lopes*, 43 anos, bancária).
  - [ ] 4. Concorrentes e Alternativas (grupos WhatsApp, lojas físicas ortopédicas, agências de home care).
  - [ ] 5. Proposta de Valor clara e direta.
  - [ ] 6. Modelo de Receita com Stripe (take rate de 12% a 15% nos plantões + assinaturas mensais de equipamentos).
  - [ ] 7. Métricas de Sucesso (MRR, GMV/Take Rate, Tempo de Atendimento < 2h, Retenção & Churn).
  - [ ] 8. Tabela completa de Lean Canvas (8 blocos preenchidos).
  - [ ] 9. Tabela do Mapa de Reaproveitamento de Arquitetura (Catálogo, RBAC, Redis, MinIO, Stripe, CI/CD).
- [ ] Incluir menção ao docente: `Prof. Allan Siriani (github.com/siriani)` e contexto da disciplina `ISW055`.
- [ ] Adicionar link de rastreabilidade para o repositório original de evidência da P1 (`https://github.com/Lebron057/tom-hanks-avestruz`).
- [ ] Adicionar seção técnica enxuta: como rodar localmente (`docker compose up`) e arquitetura de portas.

**Critérios de Aceitação (DoD):**
1. O `README.md` na raiz contém todas as 9 seções obrigatórias sem nenhuma menção ao catálogo Tom Hanks no corpo principal.
2. Contém menção explícita ao perfil `@siriani` e link `github.com/siriani`.
3. Contém link para o repositório antigo.
4. Os arquivos legados da P1 continuam disponíveis dentro de `docs/legado/`.
5. Nenhum link quebrado no documento.

---

### Issue #2 — `chore(infra): sanear docker-compose, variáveis de ambiente e expurgar dependências legadas do TMDB`

**Título da Issue:**
```
chore(infra): sanear docker-compose, variáveis de ambiente e expurgar dependências legadas do TMDB
```

**Descrição e Contexto:**
Ajustar as definições de infraestrutura local e Portainer para o novo domínio, eliminando qualquer vestígio de consumo da API TMDB (`TMDB_API_KEY`, `app/tmdb.py`), saneando o `docker-compose.yml` para provisionar automaticamente os 4 buckets do S3/Garage, adicionando healthchecks robustos em todos os serviços e sincronizando `.env.example`.

**Labels sugeridas:** `devops`, `infra`, `fase-0`

**Tarefas / Checklist de Implementação:**
- [ ] Excluir o arquivo `app/tmdb.py`.
- [ ] Remover referências a `TMDB_API_KEY` de `app/main.py`, `docker-compose.yml` e `.env.example`.
- [ ] Remover o arquivo desatualizado `docker-compose.portainer.yml` para evitar divergência de configuração (a stack oficial usará `docker-compose.yml`).
- [ ] Atualizar o script de bootstrap do `garage` no `docker-compose.yml` para criar e liberar permissão nos 4 buckets da nova aplicação: `avatars`, `equipamentos`, `credenciais` e `documentos`.
- [ ] Remover a publicação da porta host `9050:9000` do serviço `garage` no compose (mantendo apenas `expose: 9000` na rede interna `internal-net`).
- [ ] Adicionar bloco de `healthcheck` em `catalog-service`, `auth-service` e `log-service` utilizando Python nativo (`python -c "import urllib.request; urllib.request.urlopen('http://localhost:PORT/health')"`) para não depender de `curl` na imagem `python:3.11-slim`.
- [ ] Adicionar serviço `migrator` no compose (`restart: "no"`) que executa `python -m db.migrate` antes de subir os serviços da aplicação, configurando `depends_on: migrator: condition: service_completed_successfully` em `catalog-service` e `auth-service`.
- [ ] Atualizar `.env.example` com as novas variáveis (`APP_NAME=CuidaHome`, `PUBLIC_BASE_URL`, `PLATFORM_FEE_PERCENT=12`, buckets S3) e remover chaves obsoletas.
- [ ] Adicionar `backups/` ao `.gitignore`.

**Critérios de Aceitação (DoD):**
1. `docker compose build --no-cache` compila sem erros.
2. `docker compose up -d` sobe todos os serviços (`catalog-service`, `auth-service`, `log-service`, `redis`, `garage`) e `docker compose ps` reporta status `healthy` em todos.
3. O comando `git grep -in "tmdb" -- ":!docs/legado"` não retorna nenhuma ocorrência em arquivos de código ou configuração.
4. Os 4 buckets (`avatars`, `equipamentos`, `credenciais`, `documentos`) são criados no Garage na inicialização.

---

### Issue #3 — `feat(db): implementar runner de migrations versionadas e idempotentes (expand/contract)`

**Título da Issue:**
```
feat(db): implementar runner de migrations versionadas e idempotentes (expand/contract)
```

**Descrição e Contexto:**
Atualmente, as tabelas são criadas por blocos imperativos e duplicados de `init_db()` em `app/database.py` e `auth_service/database.py`. Essa abordagem tenta recriar as tabelas legadas a cada boot e não suporta migrações incrementais seguras. Esta issue introduz um runner de migrations leve em Python (sem dependência de ORMs pesados como Alembic/Flyway), com controle de locks distribuídos no MariaDB e suporte ao padrão expand/contract.

**Labels sugeridas:** `backend`, `database`, `fase-1`

**Tarefas / Checklist de Implementação:**
- [ ] Criar módulo `db/migrate.py` com suporte aos comandos:
  - `python -m db.migrate` (aplica migrações pendentes).
  - `python -m db.migrate --status` (exibe histórico de migrações aplicadas e pendentes).
  - `python -m db.migrate --dry-run` (valida sintaxe e simula aplicação).
  - `python -m db.migrate --allow-contract` (habilita migrações de contração/destrutivas como V010).
- [ ] Implementar criação da tabela de metadados `schema_migrations` (`versao`, `descricao`, `checksum`, `aplicado_em`, `duracao_ms`).
- [ ] Implementar controle de concorrência com `GET_LOCK('schema_migrations', 30)` e `RELEASE_LOCK('schema_migrations')` no MariaDB para evitar que réplicas executem migrations em paralelo.
- [ ] Validar integridade dos arquivos `.sql` já aplicados via hash SHA-256 (abortando a execução em caso de adulteração retroativa).
- [ ] Refatorar `init_db()` em `app/database.py` e `auth_service/database.py` para atuar apenas como healthcheck passivo do schema (`check_schema_version()`), emitindo warning nos logs caso existam migrations pendentes sem tentar executar DDL diretamente no boot da aplicação.
- [ ] Criar testes automatizados em `tests/test_migrations.py` validando o runner contra um banco temporário vazio e contra uma réplica do schema atual.

**Critérios de Aceitação (DoD):**
1. Executar `python -m db.migrate` em um banco limpo cria `schema_migrations` e aplica os scripts com sucesso.
2. Executar o comando pela segunda vez consecutiva resulta em *no-op* idempotente (0 migrations aplicadas, saída limpa).
3. Modificar intencionalmente o conteúdo de uma migration já aplicada faz o runner abortar com mensagem explícita de conflito de checksum.
4. O `catalog-service` e o `auth-service` inicializam sem executar comandos DDL (`CREATE/ALTER TABLE`).

---

### Issue #4 — `feat(db): modelar tabelas de plantões, locações, credenciais e arquivar schema de filmes`

**Título da Issue:**
```
feat(db): modelar tabelas de plantões, locações, credenciais e arquivar schema de filmes
```

**Descrição e Contexto:**
Modelar e versionar o conjunto completo de scripts SQL para sustentar a plataforma CuidaHome, aplicando a estratégia expand/contract. O schema legado de filmes (`favoritos` e `comentarios`) deve ser renomeado para preservação probatória, o campo `role` da tabela `usuarios` deve ser ampliado para comportar os novos papéis e todas as tabelas de saúde e locação devem ser criadas com constraints relacionais, tipagem monetária estrita em centavos (`INT UNSIGNED`) e integridade referencial.

**Labels sugeridas:** `backend`, `database`, `fase-1`

**Tarefas / Checklist de Implementação:**
- [ ] Criar `db/migrations/V001__baseline_legado.sql`: consolidação idempotente das 4 tabelas originais (`usuarios`, `reset_tokens`, `favoritos`, `comentarios`).
- [ ] Criar `db/migrations/V002__rbac_papeis_saude.sql`:
  - Ampliar `usuarios.role` para `VARCHAR(32) NOT NULL DEFAULT 'familiar_paciente'`.
  - Migrar registros existentes com `role = 'user'` para `familiar_paciente`.
  - Adicionar colunas: `telefone VARCHAR(20)`, `cidade VARCHAR(100)`, `uf CHAR(2)`, `ativo BOOLEAN DEFAULT TRUE`, `atualizado_em TIMESTAMP`.
  - Adicionar índice `idx_usuarios_role`.
- [ ] Criar `db/migrations/V003__profissionais_credenciais.sql`:
  - Tabela `perfis_profissionais` (categoria, registro_conselho, diárias em centavos, status de verificação, nota média, contadores).
  - Tabela `credenciais` (tipo de documento, chave S3, MIME, status de aprovação, motivo de rejeição, validade).
  - Tabela `disponibilidades` (dia da semana, turnos aceitos).
- [ ] Criar `db/migrations/V004__pacientes_documentos.sql`:
  - Tabela `pacientes` (familiar_id, nome, data_nascimento, cidade, condicao_resumo, mobilidade).
  - Tabela `documentos` (paciente_id, locacao_id, chave S3, tipo_documento, visibilidade).
- [ ] Criar `db/migrations/V005__plantoes.sql`:
  - Tabela `plantoes` (familiar_id, paciente_id, profissional_id, modalidade, diária, taxas, repasse em centavos, status de ciclo de vida).
  - Tabela `candidaturas_plantao` (para concorrência de profissionais no mural aberto).
  - Tabela `avaliacoes` (nota de 1 a 5, comentário, resposta, status de moderação).
  - Tabela `repasses` (beneficiário, valor bruto, taxa da plataforma, valor líquido, status de liberação).
- [ ] Criar `db/migrations/V006__catalogo_equipamentos.sql`:
  - Tabela `categorias_equipamento` (slug, nome, descrição, ícone).
  - Tabela `equipamentos` (fornecedor_id, categoria_id, nome, preço mensal em centavos, valor de caução em centavos, stripe_price_id).
  - Tabela `fotos_equipamento` (chave S3, ordem).
  - Tabela `unidades_equipamento` (número de patrimônio/série, status de disponibilidade física).
- [ ] Criar `db/migrations/V007__locacoes_caucoes.sql`:
  - Tabela `locacoes` (cliente_id, equipamento_id, unidade_id, endereço, status de logística, stripe_subscription_id).
  - Tabela `caucoes` (locacao_id, stripe_payment_intent_id, valor_centavos, status, capture_before).
  - Tabela `movimentacoes_locacao` (rastreamento de despacho, entrega, recolhimento).
  - Tabela `contratos` (registro do aceite digital de termos de locação/plantão).
- [ ] Criar `db/migrations/V008__stripe_eventos_seeds.sql`:
  - Tabela `stripe_eventos` (event_id PK, tipo, processado_em) para idempotência de webhooks.
  - Seeds iniciais de `categorias_equipamento` (Cadeiras de Rodas, Camas Hospitalares, Andadores e Muletas, Suportes e Acessórios).
- [ ] Criar `db/migrations/V009__arquivar_legado_filmes.sql`:
  - Renomear `favoritos` para `legacy_favoritos_filmes`.
  - Renomear `comentarios` para `legacy_comentarios_filmes`.
  - Criar nova tabela polimórfica `favoritos` (`usuario_id`, `alvo_tipo ENUM('profissional','equipamento')`, `alvo_id`).
- [ ] Criar `db/migrations/V010__contract.sql` (fase de contração manual futura):
  - Exclusão das tabelas `legacy_*`, remoção de `usuarios.premium` e `usuarios.stripe_subscription_id`, adição de constraint CHECK em `usuarios.role`.
- [ ] Atualizar `schema.sql` na raiz como cópia de referência consolidada do schema.

**Critérios de Aceitação (DoD):**
1. Migrações V001 até V009 executam sequencialmente sem erros no MariaDB 11.8.
2. Os dados pré-existentes de `usuarios` permanecem intactos, com a coluna `role` convertida de `user` para `familiar_paciente`.
3. As 8 linhas de `favoritos` e 2 de `comentarios` do legado continuam acessíveis nas tabelas `legacy_*`.
4. Todos os campos monetários utilizam tipo inteiro sem sinal (`INT UNSIGNED`), representando valores em centavos.
5. As chaves estrangeiras com `ON DELETE CASCADE` ou `ON DELETE RESTRICT` mantêm consistência referencial estrita.

---

### Issue #5 — `feat(auth): expandir RBAC com 4 novos papéis, atributos complementares e autocadastro qualificado`

**Título da Issue:**
```
feat(auth): expandir RBAC com 4 novos papéis, atributos complementares e autocadastro qualificado
```

**Descrição e Contexto:**
Evoluir o sistema de autenticação e RBAC do projeto para suportar a matriz de 4 papéis de negócio: `admin`, `profissional_saude`, `familiar_paciente` e `fornecedor_equipamento`. Deve-se manter a arquitetura do Padrão A (enforcement centralizado consultando o banco em tempo real via `/auth/verify`) e Padrão B no JWT, adicionando validações de atributos contextuais (ABAC: ex: profissional só aceita plantão se tiver credencial aprovada) e blindando o autocadastro contra escalada de privilégio para `admin`.

**Labels sugeridas:** `auth`, `security`, `fase-2`

**Tarefas / Checklist de Implementação:**
- [ ] Atualizar schemas Pydantic no `auth_service/models.py` para validar os 4 papéis no registro e nas claims do token JWT.
- [ ] Blindar o endpoint `POST /auth/register` no `auth-service` para proibir categoricamente a atribuição de `role = 'admin'` via payload público (retornar 400 Bad Request se tentado). Papéis permitidos no cadastro público: `familiar_paciente` (default), `profissional_saude`, `fornecedor_equipamento`.
- [ ] Atualizar tela de cadastro (`app/templates/register.html`) para permitir que o usuário selecione seu perfil de atuação (Familiar/Paciente, Profissional de Saúde ou Fornecedor de Equipamentos).
- [ ] Implementar dependências FastAPI em `app/deps.py`:
  - `require_roles(*roles)`: valida se o usuário autenticado possui um dos papéis requeridos (HTTP 403 em caso negativo).
  - `require_verified_professional()`: valida se o usuário possui `role = 'profissional_saude'` E registro correspondente em `perfis_profissionais` com `status_verificacao = 'aprovado'`.
  - `require_owner_or_admin(resource_owner_id)`: proteção estrita contra IDOR.
- [ ] Atualizar o `log-service` para incluir o campo `ator_role` nos eventos persistidos no Redis Stream.
- [ ] Criar testes unitários e de integração em `tests/test_rbac.py` cobrindo a matriz de permissões (garantir retorno 403 para acessos cruzados não autorizados).

**Critérios de Aceitação (DoD):**
1. Requisições sem autenticação para rotas protegidas retornam HTTP 401 ou redirecionam para `/login`.
2. Requisição autenticada de `familiar_paciente` tentando acessar endpoints de fornecedor ou aprovação admin retorna estritamente **HTTP 403 Forbidden**.
3. Tentativa de cadastro com `role = 'admin'` via API é rejeitada com HTTP 400.
4. Profissional cadastrado com status `pendente` recebe HTTP 403 ao tentar aceitar plantões no mural.
5. Cada negação de acesso (403) dispara evento `audit.security.access_denied` no Redis.

---

### Issue #6 — `feat(storage): reestruturar S3/Garage em 4 buckets com proxy autenticado para credenciais e laudos`

**Título da Issue:**
```
feat(storage): reestruturar S3/Garage em 4 buckets com proxy autenticado para credenciais e laudos
```

**Descrição e Contexto:**
Substituir o modelo monobucket anterior (`avatars`) por uma arquitetura com 4 buckets especializados: `avatars`, `equipamentos`, `credenciais` e `documentos`. Como o storage subjacente (Garage v0.9) não suporta políticas de bucket complexas e não está exposto publicamente na internet, todo o acesso a documentos privados e sensíveis (laudos de pacientes, diplomas, certidões e vistorias) deve ser obrigatoriamente intermediado por endpoints de streaming autenticados no `catalog-service`, com validação rigorosa de MIME types, magic bytes e RBAC.

**Labels sugeridas:** `storage`, `security`, `fase-3`

**Tarefas / Checklist de Implementação:**
- [ ] Refatorar `app/minio_client.py` para módulo multi-bucket `app/services/storage.py`, suportando configuração via variáveis de ambiente com defaults seguros.
- [ ] Criar função de inicialização `ensure_buckets()` que valida e provisiona idempotentemente os 4 buckets (`avatars`, `equipamentos`, `credenciais`, `documentos`).
- [ ] Implementar validação profunda de uploads:
  - Tamanho máximo configurável por categoria (3 MB para avatares; 5 MB para equipamentos; 10 MB para documentos/credenciais em PDF).
  - Validação de magic bytes (primeiros bytes do arquivo) para evitar upload malicioso com extensão alterada (`%PDF` para PDFs, `FFD8FF` para JPG, `89504E47` para PNG, `RIFF...WEBP` para WEBP).
  - Geração de chave de objeto randômica sem manter o nome original do arquivo (`{prefixo}/{id}/{timestamp}-{hex_aleatorio}.{ext}`).
- [ ] Implementar rotas públicas de proxy de imagens:
  - `GET /storage/avatars/{filename}`
  - `GET /storage/equipamentos/{equipamento_id}/{filename}`
- [ ] Implementar rotas privadas de proxy de documentos protegidos por RBAC:
  - `GET /documentos/credenciais/{credencial_id}`: acessível apenas pelo dono do documento e por administradores.
  - `GET /documentos/laudos/{documento_id}`: acessível apenas pelo familiar responsável, pelo profissional com plantão ativo com o paciente e por administradores.
  - `GET /documentos/vistoria/{movimentacao_id}`: acessível pelo cliente, fornecedor e administrador.
- [ ] Configurar cabeçalhos HTTP de segurança nas respostas de streaming: `Content-Disposition: attachment` para PDFs, `X-Content-Type-Options: nosniff` e `Cache-Control: private, no-transform`.
- [ ] Disparar evento de auditoria `documento.acessado` a cada leitura de arquivo privado.

**Critérios de Aceitação (DoD):**
1. O upload de um arquivo com extensão `.pdf` contendo binário de executável é rejeitado com HTTP 400 (falha na validação de magic bytes).
2. Um usuário autenticado como `familiar_paciente` recebe **HTTP 403** ao tentar fazer download da credencial de um profissional pela rota `/documentos/credenciais/{id}`.
3. O administrador consegue visualizar qualquer credencial para fins de auditoria/aprovação.
4. Substituição ou exclusão de foto/documento remove o objeto antigo do storage, impedindo acúmulo de arquivos órfãos.

---

### Issue #7 — `feat(plantoes): implementar ciclo de contratação de plantões (direto e mural) com ledger de repasses`

**Título da Issue:**
```
feat(plantoes): implementar ciclo de contratação de plantões (direto e mural) com ledger de repasses
```

**Descrição e Contexto:**
Implementar o motor de negócio para a gestão de plantões de cuidadores e profissionais de enfermagem em domicílio. O sistema deve suportar duas modalidades: contratação direta de um profissional específico e solicitação aberta no mural para atendimentos emergenciais com concorrência atômica entre profissionais validados. O fluxo integra o pagamento da diária e taxa de intermediação (take rate de 12% a 15%) via Stripe Checkout e registra o balanço no ledger de repasses.

**Labels sugeridas:** `backend`, `business-logic`, `fase-4`

**Tarefas / Checklist de Implementação:**
- [ ] Implementar serviço de cálculo financeiro (`app/services/pricing.py`):
  - Cálculo de diária de 12h ou 24h.
  - Aplicação do percentual de taxa da plataforma (`PLATFORM_FEE_PERCENT`, default 12%).
  - Cálculo do repasse líquido do profissional (`valor_repasse = valor_diaria - taxa`).
- [ ] Criar endpoint `POST /plantoes/novo`:
  - Modalidade direta: vincula `familiar_id`, `paciente_id` e `profissional_id` no status `solicitado`.
  - Modalidade mural (emergencial): deixa `profissional_id = NULL` e status `aberto`.
- [ ] Implementar máquina de estados e ações de transição em `app/routers/plantoes.py`:
  - `POST /plantoes/{id}/aceitar`: profissional aceita o plantão. No mural aberto, implementar lock otimista no MariaDB (`UPDATE plantoes SET profissional_id = %s, status = 'aguardando_pagamento' WHERE id = %s AND status = 'aberto'`) auxiliado por chave transitória no Redis (`SET lock:plantao:{id} NX EX 15`) para eliminar condições de corrida (*race condition*).
  - `POST /plantoes/{id}/recusar`: profissional recusa solicitação direta (plantão transiciona para `cancelado`).
  - `POST /plantoes/{id}/pagar`: familiar gera Checkout Session no Stripe no valor da diária total.
  - `POST /plantoes/{id}/checkin` e `POST /plantoes/{id}/checkout`: registro de início e fim da escala com timestamp.
  - `POST /plantoes/{id}/cancelar`: cancelamento com regras de reembolso baseadas na antecedência.
- [ ] Integrar webhook do Stripe para o evento `checkout.session.completed` com `metadata.tipo = 'plantao'`:
  - Atualiza status do plantão para `confirmado`.
  - Cria registro correspondente na tabela `repasses` com status `pendente`.
- [ ] Liberar repasse para o profissional (`status = 'liberado'`) automaticamente após a conclusão bem-sucedida do plantão (`checkout` realizado).
- [ ] Emitir eventos correspondentes no Redis a cada mudança de estado (`plantao.solicitado`, `plantao.aceito`, `plantao.confirmado`, `plantao.concluido`).

**Critérios de Aceitação (DoD):**
1. Teste de concorrência: 5 requisições simultâneas de profissionais diferentes tentando aceitar o mesmo plantão do mural resultam em exatamente 1 sucesso (200) e 4 conflitos (409 Conflict ou 400).
2. O webhook da Stripe marca o plantão como `confirmado` e grava a linha no ledger `repasses` com o cálculo exato de centavos.
3. Não é possível realizar `checkin` em plantão não pago (`confirmado`).
4. Familiar só consegue avaliar o profissional após o plantão estar no estado `concluido`.

---

### Issue #8 — `feat(locacoes): implementar locação de equipamentos com Stripe Billing recorrente e caução`

**Título da Issue:**
```
feat(locacoes): implementar locação de equipamentos com Stripe Billing recorrente e caução
```

**Descrição e Contexto:**
Implementar o motor de locação de equipamentos ortopédicos e hospitalares (cadeiras de rodas, camas articuladas, andadores). O modelo combina faturamento recorrente mensal via Stripe Billing (renovação automática a cada 30 dias até a solicitação de devolução) e pré-autorização de garantia/caução no cartão de crédito do cliente, cobrindo eventuais avarias ou perda do patrimônio durante o período de uso.

**Labels sugeridas:** `backend`, `stripe`, `fase-5`

**Tarefas / Checklist de Implementação:**
- [ ] Criar script `scripts/stripe_seed_prices.py` para criar produtos e preços recorrentes mensais no Stripe (Modo de Teste) e persistir os `stripe_price_id` correspondentes na tabela `equipamentos`.
- [ ] Implementar fluxo de contratação de locação (`POST /equipamentos/{id}/locar`):
  - Registra a locação no MariaDB com status `pendente_pagamento`.
  - Registra o aceite formal do termo de locação na tabela `contratos` (com IP e timestamp).
  - Cria Checkout Session no Stripe em `mode = 'subscription'`, associando o `stripe_price_id` mensal do equipamento e metadados (`tipo = 'locacao'`, `locacao_id`).
- [ ] Processar webhooks do ciclo de vida de assinaturas da Stripe:
  - `checkout.session.completed` (`tipo = 'locacao'`):
    - Associa `stripe_subscription_id` e `stripe_customer_id` à locação.
    - Dispara autorização de caução via `stripe.PaymentIntent.create(capture_method='manual', off_session=True)` utilizando a forma de pagamento salva do cliente.
    - Atualiza status da locação para `em_separacao`.
  - `payment_intent.amount_capturable_updated`:
    - Atualiza status da caução para `autorizada` e grava o timestamp `capture_before`.
  - `invoice.paid` (`billing_reason = 'subscription_cycle'`):
    - Emite evento `locacao.renovada` no Redis e gera repasse mensal ao fornecedor.
  - `invoice.payment_failed`:
    - Atualiza locação para `inadimplente` e notifica familiar e fornecedor.
- [ ] Implementar fluxo de solicitação de devolução e encerramento:
  - `POST /painel/familia/locacoes/{id}/devolver`: cliente solicita recolhimento; locação vai para `devolucao_solicitada`.
  - `POST /painel/fornecedor/locacoes/{id}/recolhido`: fornecedor confirma recolhimento físico e realiza vistoria com upload de fotos.
  - Se vistoria OK: cancela o PaymentIntent da caução no Stripe (`stripe.PaymentIntent.cancel`) e encerra a assinatura (`stripe.Subscription.modify(cancel_at_period_end=True)`).
  - Se avaria detectada: fornecedor aciona admin para captura parcial ou total do valor autorizado (`stripe.PaymentIntent.capture`).

**Critérios de Aceitação (DoD):**
1. Ao concluir o checkout de locação em modo de teste com cartão de teste da Stripe, a locação transiciona para `em_separacao` e uma autorização de caução é gerada.
2. O webhook `invoice.paid` de renovação periódica registra o evento de renovação no Redis sem duplicar locações.
3. Solicitação de devolução com vistoria aprovada libera a autorização de caução sem debitar o valor do cliente.
4. Tentativa de locação em equipamento sem unidades físicas disponíveis no estoque retorna mensagem amigável de indisponibilidade.

---

### Issue #9 — `feat(events): estruturar trilha de eventos de negócio no Redis Streams e métricas de auditoria`

**Título da Issue:**
```
feat(events): estruturar trilha de eventos de negócio no Redis Streams e métricas de auditoria
```

**Descrição e Contexto:**
Evoluir o microsserviço `log-service` e as integrações com Redis para registrar eventos de negócio estruturados em múltiplos Redis Streams organizados por domínio (`evt:plantao`, `evt:locacao`, `evt:pagamento`, `evt:credencial`), preservando o stream central de auditoria `log:eventos`. O sistema deve manter sorted sets para reconstrução de linhas do tempo das entidades e manter contadores agregados diários para exibição instantânea no painel administrativo sem sobrecarregar o banco relacional.

**Labels sugeridas:** `redis`, `events`, `fase-4`

**Tarefas / Checklist de Implementação:**
- [ ] Atualizar contrato do `LogEvent` em `log_service/main.py` com campos opcionais tipados: `categoria`, `ator_role`, `entidade`, `entidade_id`, `dados` (dicionário serializável em JSON).
- [ ] Manter compatibilidade com eventos legados (garantir que chamadas enviando apenas `usuario_id`, `acao`, `detalhe` continuem funcionando sem quebra).
- [ ] Ao receber um evento no endpoint `POST /logs`:
  - Gravar no stream mestre `log:eventos` (com `MAXLEN ~ 50000`).
  - Identificar o domínio pelo prefixo de `acao` e gravar no stream específico correspondente (ex: `acao = 'plantao.solicitado'` grava também em `evt:plantao`).
  - Se `entidade` e `entidade_id` estiverem presentes, adicionar entrada no Sorted Set `idx:{entidade}:{entidade_id}` com timestamp como score para busca de linha do tempo.
  - Incrementar chave de agregação diária `metrics:{yyyy-mm-dd}:{acao}` via `INCR` com TTL de 90 dias.
  - Para eventos de match de plantão (`plantao.aceito`), calcular a diferença em minutos desde a criação e atualizar o hash `metrics:tempo_match:{yyyy-mm}` para cálculo do tempo médio de atendimento (KPI < 2h).
- [ ] Implementar endpoint interno `GET /logs/timeline/{entidade}/{entidade_id}` protegido por autenticação para alimentar a exibição da linha do tempo na interface web.
- [ ] Criar testes cobrindo persistência e recuperação de eventos no Redis em `tests/test_events.py`.

**Critérios de Aceitação (DoD):**
1. O disparo de uma ação de negócio persiste o evento simultaneamente em `log:eventos` e no stream especializado do domínio.
2. A consulta da linha do tempo de um plantão retorna todos os eventos ordenados cronologicamente.
3. Se o Redis estiver temporariamente fora do ar, o `catalog-service` não interrompe a operação do usuário (resiliência *best-effort* mantida).
4. Dados sensíveis de saúde (diagnósticos, prontuários, CPFs) nunca são incluídos nos payloads gravados nos streams do Redis.

---

### Issue #10 — `feat(ui): implementar Landing Page, Catálogo de Equipamentos e Mural de Profissionais`

**Título da Issue:**
```
feat(ui): implementar Landing Page, Catálogo de Equipamentos e Mural de Profissionais
```

**Descrição e Contexto:**
Construir as interfaces públicas e de catálogo da plataforma CuidaHome, implementando design responsivo *mobile-first*, paleta de cores orientada à área de saúde (tons de azul/verde/teal) com contraste visual aderente às diretrizes de acessibilidade WCAG AA e tipografia legível para familiares e idosos. As views substituem integralmente o catálogo antigo de filmes.

**Labels sugeridas:** `frontend`, `ui`, `fase-6`

**Tarefas / Checklist de Implementação:**
- [ ] Redesenhar folha de estilos `app/static/style.css`:
  - Definir design tokens (paleta de saúde, tipografia legível, espaçamentos consistentes).
  - Componentizar cards de profissionais, cards de equipamentos, badges de status e banners de alerta.
- [ ] Atualizar `app/templates/base.html`:
  - Navbar contextualizada para CuidaHome com menu adaptado ao papel do usuário logado.
  - Rodapé institucional com informações de suporte, termos de uso e selo acadêmico (`ISW055 / FATEC`).
- [ ] Implementar `app/templates/public/landing.html` (rota `/`):
  - Seção Hero com proposta de valor clara e barra de busca integrada (cidade + especialidade/equipamento).
  - Vitrine com 6 profissionais verificados em destaque (ordenados por nota).
  - Vitrine com 6 equipamentos disponíveis para locação imediata.
  - Bloco explicativo "Como Funciona" em 3 passos ilustrados.
  - CTAs dedicados para cadastro de cuidadores/enfermeiros e fornecedores de equipamentos.
- [ ] Implementar `app/templates/equipamentos/catalogo.html` e `detalhe.html`:
  - Filtros por categoria ortopédica, faixa de preço mensal e disponibilidade imediata.
  - Galeria de fotos servida pelo proxy S3, especificações técnicas, valor do aluguel/mês e valor da caução.
  - Botão de contratação "Alugar Agora" disparando o modal/fluxo de locação.
- [ ] Implementar `app/templates/profissionais/mural.html` e `detalhe.html`:
  - Filtros por categoria profissional (Cuidador, Técnico de Enfermagem, Enfermeiro), cidade/UF, turno de atendimento e valor de diária.
  - Exibição de selo "COREN Verificado", avaliações de outros familiares e nota média.
  - Botão "Solicitar Plantão" vinculado à abertura do formulário de solicitação.

**Critérios de Aceitação (DoD):**
1. Todas as telas renderizam sem erros de sintaxe Jinja2 ou estilos quebrados tanto em desktop quanto em telas móveis (375px de largura).
2. Profissionais com status de verificação diferente de `aprovado` **nunca** aparecem na listagem pública.
3. Equipamentos sem estoque físico exibem badge visual de "Indisponível no momento" com botão de locação desabilitado.
4. Nenhuma referência a atores, pôsteres de filmes ou TMDB está presente no HTML gerado.

---

### Issue #11 — `feat(ui): implementar painéis dedicados (Familiar, Profissional, Fornecedor e Admin)`

**Título da Issue:**
```
feat(ui): implementar painéis dedicados (Familiar, Profissional, Fornecedor e Admin)
```

**Descrição e Contexto:**
Construir as áreas restritas e painéis operacionais (*dashboards*) de cada um dos 4 papéis do ecossistema, garantindo que cada usuário visualize estritamente os dados e controles pertinentes ao seu escopo de atuação.

**Labels sugeridas:** `frontend`, `ui`, `fase-6`

**Tarefas / Checklist de Implementação:**
- [ ] **Painel do Familiar / Paciente (`/painel/familia`):**
  - Visão geral: plantões agendados, equipamentos locados e pendências de avaliação.
  - Aba de Pacientes: cadastro/edição de familiares dependentes com upload seguro de laudos médicos.
  - Aba de Locações: status logístico da entrega, data da próxima renovação e botão "Solicitar Devolução".
  - Aba de Histórico de Plantões com botão de check-out e formulário de avaliação do cuidador.
- [ ] **Painel do Profissional de Saúde (`/painel/profissional`):**
  - Visão geral de escala: próximos plantões confirmados com endereço e recomendações do paciente.
  - Gestão de Agenda: definição de disponibilidade de dias e turnos.
  - Central de Credenciais: upload de diploma, carteira do COREN e certidão de antecedentes com visualização de status (Pendente / Aprovado / Rejeitado) e feedback de inconsistências.
  - Extrato Financeiro: listagem de repasses (bruto, taxa retida, líquido e data de pagamento).
- [ ] **Painel do Fornecedor / Locador (`/painel/fornecedor`):**
  - Gestão de Equipamentos e Unidades físicas (número de patrimônio/série e status).
  - Fila Logística: pedidos aguardando despacho, entregas a confirmar e coletas de devolução agendadas.
  - Registro de Vistoria: upload de fotos do estado físico do equipamento na entrega e na devolução.
- [ ] **Painel Administrativo (`/admin`):**
  - Dashboard Executivo: indicadores consolidados (MRR de locações, GMV de plantões, take rate retido e tempo médio de atendimento).
  - Fila de Validação de Credenciais: visualização de documentos de profissionais com ações de aprovar ou rejeitar (com campo para justificativa).
  - Moderação de Avaliações e Usuários.
  - Consulta de Logs de Auditoria (`/admin/logs` — reaproveitada do projeto anterior).

**Critérios de Aceitação (DoD):**
1. O acesso a cada painel é estritamente condicionado ao papel do usuário logado (redirecionamento ou 403 para tentativas não autorizadas).
2. O formulário de upload de laudos no painel da família vincula o arquivo ao bucket privado `documentos` e valida o tamanho máximo de 10 MB.
3. O administrador consegue aprovar uma credencial pendente, o que reflete imediatamente na liberação do profissional para aceitar plantões.
4. O extrato financeiro do profissional exibe a dedução transparente do percentual de taxa da plataforma.

---

### Issue #12 — `ops: documentar e executar o runbook de deploy contínuo no Portainer e validação em produção`

**Título da Issue:**
```
ops: documentar e executar o runbook de deploy contínuo no Portainer e validação em produção
```

**Descrição e Contexto:**
Documentar formalmente e validar em produção o procedimento operacional padrão (SOP / Runbook) para atualização da stack do Portainer no cluster do laboratório (`portainer.lapps.studio`). O processo deve garantir zero perda de dados no MariaDB e nos volumes de dados do Redis e Garage, detalhando o processo de backup pré-deploy, sincronização de variáveis de ambiente, execução das migrations do banco via container e validação via smoke tests na URL pública.

**Labels sugeridas:** `devops`, `documentation`, `ops`, `fase-0`

**Tarefas / Checklist de Implementação:**
- [ ] Criar documento `docs/RUNBOOK_DEPLOY.md` estruturando o passo a passo operacional completo.
- [ ] Criar script `scripts/smoke_test.py` para validação automatizada pós-deploy:
  - Checagem do endpoint `/health` de todos os serviços.
  - Validação de renderização da Landing Page e Catálogo.
  - Validação de isolamento RBAC (tentativa anônima em rota privada retornando 302/401).
- [ ] Documentar procedimento de backup lógico pré-deploy via `mariadb-dump` executado a partir de container Docker local (evitando problemas de codificação UTF-16 no Windows PowerShell).
- [ ] Documentar checklist de configuração no painel do Portainer:
  - Edição do repositório Git da stack para `https://github.com/Lebron057/saude-domiciliar.git`.
  - Atualização do bloco de variáveis de ambiente (remoção de `TMDB_API_KEY`, inclusão de novas variáveis).
  - Execução de *Update the stack* com pull de novas imagens e build no servidor.
- [ ] Documentar procedimento de rollback de emergência em duas vias:
  - Rollback de código (retorno da stack para a tag Git `v1-catalogo-filmes-final`).
  - Rollback de banco de dados (restauração do arquivo de dump SQL via container mariadb).
- [ ] Executar o procedimento em ambiente de homologação/produção e anexar evidências de execução nos logs da issue.

**Critérios de Aceitação (DoD):**
1. O arquivo `docs/RUNBOOK_DEPLOY.md` está versionado e detalha todos os passos operacionais sem ambiguidades.
2. O script `scripts/smoke_test.py` executa e passa 100% dos testes contra o subdomínio público `iago-lima-isw055.lapps.studio`.
3. Os containers sobem no Portainer escutando estritamente na porta reservada do aluno (`8210`), garantindo o roteamento correto pelo túnel FRP.
4. Os dados legados de usuários continuam preservados no MariaDB após a migração.

---

### Template Extra: Issue de Entrega da Atividade 9 (Menção `@siriani`)

> **Observação:** Esta issue deve ser aberta no repositório `https://github.com/Lebron057/saude-domiciliar` após a conclusão das Fases 0 e 1, conforme especificado na seção 7 das instruções da atividade.

**Título da Issue:**
```
Entrega Fork e plano de negócio
```

**Conteúdo da Issue:**
```markdown
Prezado professor @siriani,

Conforme solicitado nas diretrizes da **Atividade 9 (Fork e Plano de Negócio)** da disciplina de *Introdução à Computação em Nuvem (ISW055)*, apresento a entrega referente à transição do projeto para a plataforma **CuidaHome (Saúde & Atendimento Domiciliar)**.

### 1. Dados e Links do Projeto
* **Repositório Novo (SaaS):** https://github.com/Lebron057/saude-domiciliar
* **Repositório Anterior (Evidência P1 mantida intacta):** https://github.com/Lebron057/tom-hanks-avestruz
* **Redirecionamento no Repositório Antigo:** Linha de encaminhamento devidamente inserida no topo do README de origem.
* **Commit do novo README e Plano:** [Link do commit correspondente no GitHub]

---

### 2. Resumo da Transição e Modelo de Negócio
* **Nicho Escolhido:** Saúde & Atendimento Domiciliar (Plantões de Cuidadores/Enfermagem e Locação de Equipamentos Ortopédicos/Hospitalares).
* **README Reestruturado:** O novo `README.md` foi preenchido integralmente contemplando as 9 seções obrigatórias:
  1. Nome e Frase de impacto (*CuidaHome*).
  2. A Dor (famílias desamparadas pós-alta hospitalar e traumas súbitos).
  3. Persona (*Mariana Lopes*, 43 anos, bancária).
  4. Concorrentes e Alternativas (WhatsApp informal, lojas físicas de ortopedia, agências tradicionais de home care).
  5. Proposta de Valor.
  6. Modelo de Receita com Stripe (Take rate de 12% a 15% por plantão intermediado + assinaturas mensais recorrentes para locação de equipamentos com retenção de caução).
  7. Métricas de Sucesso (MRR, GMV, Tempo de Match < 2h, Churn controlado).
  8. Lean Canvas completo (8 blocos de negócio).
  9. Mapa de Reaproveitamento de Arquitetura (Mapeamento 1:1 de TMDB, RBAC, Redis, MinIO, Stripe e CI/CD).

---

### 3. Backlog de Desenvolvimento
Foram cadastradas **12 issues técnicas e granulares** no repositório, divididas por fases operacionais com checklists de tarefas e critérios de aceitação (DoD) estritos, servindo como guia de implementação para as próximas entregas práticas:
1. `docs: estruturar novo README.md com modelo de negócio e mapa de migração`
2. `chore(infra): sanear docker-compose, variáveis de ambiente e expurgar dependências legadas do TMDB`
3. `feat(db): implementar runner de migrations versionadas e idempotentes (expand/contract)`
4. `feat(db): modelar tabelas de plantões, locações, credenciais e arquivar schema de filmes`
5. `feat(auth): expandir RBAC com 4 novos papéis, atributos complementares e autocadastro qualificado`
6. `feat(storage): reestruturar S3/Garage em 4 buckets com proxy autenticado para credenciais e laudos`
7. `feat(plantoes): implementar ciclo de contratação de plantões (direto e mural) com ledger de repasses`
8. `feat(locacoes): implementar locação de equipamentos com Stripe Billing recorrente e caução`
9. `feat(events): estruturar trilha de eventos de negócio no Redis Streams e métricas de auditoria`
10. `feat(ui): implementar Landing Page, Catálogo de Equipamentos e Mural de Profissionais`
11. `feat(ui): implementar painéis dedicados (Familiar, Profissional, Fornecedor e Admin)`
12. `ops: documentar e executar o runbook de deploy contínuo no Portainer e validação em produção`

---

### 4. Evidências Anexadas (Prints)
*(Anexar aqui as imagens abaixo antes de enviar a issue)*
1. **Print da aba *Commits*:** Comprovando a preservação do histórico de commits da P1 e o novo commit de reestruturação do README.
2. **Print da aba *Issues*:** Mostrando o backlog das issues cadastradas no repositório `saude-domiciliar`.
```
