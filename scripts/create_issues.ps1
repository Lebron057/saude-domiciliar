# PowerShell Script: Criação automatizada das 12 issues do backlog CuidaHome via GitHub CLI (gh)
# Pré-requisito: gh auth login executado com sucesso.

$ErrorActionPreference = "Stop"

# Verifica se o gh está instalado
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Error "O comando 'gh' não foi encontrado. Instale com: winget install --id GitHub.cli e reinicie o terminal."
}

# Verifica se está autenticado
$authCheck = gh auth status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "Você não está autenticado no GitHub CLI. Execute primeiro: gh auth login"
}

Write-Host "Autenticação no GitHub verificada com sucesso!" -ForegroundColor Green
Write-Host "Iniciando criação das 12 issues no repositório..." -ForegroundColor Cyan

$issues = @(
    @{
        Title = "docs: estruturar novo README.md com modelo de negócio e mapa de migração"
        Body = @"
### Descrição e Contexto
Adequar a documentação principal do repositório saude-domiciliar substituindo completamente o tema antigo de Catálogo de Filmes do Tom Hanks pelas diretrizes do novo produto **CuidaHome (Saúde & Atendimento Domiciliar)**, respeitando estritamente a ordem de 9 seções exigida na Atividade 9 e adicionando menção ao docente `@siriani`. Os arquivos de documentação antigos da P1 devem ser preservados em `docs/legado/` para histórico.

### Tarefas / Checklist de Implementação
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

### Critérios de Aceitação (DoD)
1. O `README.md` na raiz contém todas as 9 seções obrigatórias sem nenhuma menção ao catálogo Tom Hanks no corpo principal.
2. Contém menção explícita ao perfil `@siriani` e link `github.com/siriani`.
3. Contém link para o repositório antigo.
4. Os arquivos legados da P1 continuam disponíveis dentro de `docs/legado/`.
5. Nenhum link quebrado no documento.
"@
    },
    @{
        Title = "chore(infra): sanear docker-compose, variáveis de ambiente e expurgar dependências legadas do TMDB"
        Body = @"
### Descrição e Contexto
Ajustar as definições de infraestrutura local e Portainer para o novo domínio, eliminando qualquer vestígio de consumo da API TMDB (`TMDB_API_KEY`, `app/tmdb.py`), saneando o `docker-compose.yml` para provisionar automaticamente os 4 buckets do S3/Garage, adicionando healthchecks robustos em todos os serviços e sincronizando `.env.example`.

### Tarefas / Checklist de Implementação
- [ ] Excluir o arquivo `app/tmdb.py`.
- [ ] Remover referências a `TMDB_API_KEY` de `app/main.py`, `docker-compose.yml` e `.env.example`.
- [ ] Remover o arquivo desatualizado `docker-compose.portainer.yml` para evitar divergência de configuração.
- [ ] Atualizar o script de bootstrap do `garage` no `docker-compose.yml` para criar e liberar permissão nos 4 buckets: `avatars`, `equipamentos`, `credenciais` e `documentos`.
- [ ] Remover a publicação da porta host `9050:9000` do serviço `garage` no compose (mantendo apenas `expose: 9000`).
- [ ] Adicionar bloco de `healthcheck` em `catalog-service`, `auth-service` e `log-service` utilizando Python nativo.
- [ ] Adicionar serviço `migrator` no compose (`restart: 'no'`) executando `python -m db.migrate`.
- [ ] Atualizar `.env.example` com as novas variáveis e remover chaves obsoletas.
- [ ] Adicionar `backups/` ao `.gitignore`.

### Critérios de Aceitação (DoD)
1. `docker compose build --no-cache` compila sem erros.
2. `docker compose up -d` sobe todos os serviços com status `healthy`.
3. `git grep -in "tmdb"` não retorna nenhuma ocorrência em arquivos de código ou configuração.
4. Os 4 buckets são criados no Garage na inicialização.
"@
    },
    @{
        Title = "feat(db): implementar runner de migrations versionadas e idempotentes (expand/contract)"
        Body = @"
### Descrição e Contexto
Implementar um runner de migrations determinístico e idempotente em Python sem dependência de ORMs externos, utilizando a tabela `schema_migrations`, controle de concorrência com `GET_LOCK` no MariaDB e suporte ao padrão expand/contract.

### Tarefas / Checklist de Implementação
- [ ] Criar módulo `db/migrate.py` com suporte aos comandos:
  - `python -m db.migrate` (aplica pendentes).
  - `python -m db.migrate --status` (histórico).
  - `python -m db.migrate --dry-run` (simulação).
  - `python -m db.migrate --allow-contract` (habilita migrações destrutivas).
- [ ] Criar tabela de metadados `schema_migrations`.
- [ ] Implementar controle de lock distribuído com `GET_LOCK('schema_migrations', 30)`.
- [ ] Validar integridade via hash SHA-256.
- [ ] Refatorar `init_db()` em `app/database.py` e `auth_service/database.py` para atuar como healthcheck passivo do schema (`check_schema_version()`).
- [ ] Criar testes automatizados em `tests/test_migrations.py`.

### Critérios de Aceitação (DoD)
1. `python -m db.migrate` aplica scripts com sucesso.
2. Segunda execução consecutiva é no-op idempotente.
3. Alteração no hash de migration já aplicada acusa erro de integridade.
4. Aplicação inicia sem executar comandos DDL no boot.
"@
    },
    @{
        Title = "feat(db): modelar tabelas de plantões, locações, credenciais e arquivar schema de filmes"
        Body = @"
### Descrição e Contexto
Modelar o schema relacional da nova plataforma de Saúde e Locação Ortopédica no MariaDB 11.8. O schema legado de filmes é renomeado para preservação probatória, o campo `role` é expandido para `VARCHAR(32)` e todas as novas tabelas são criadas com tipos monetários em centavos (`INT UNSIGNED`).

### Tarefas / Checklist de Implementação
- [ ] `V001__baseline_legado.sql`: consolidação idempotente das 4 tabelas originais.
- [ ] `V002__rbac_papeis_saude.sql`: expande `usuarios.role` para `VARCHAR(32)`, converte `user` -> `familiar_paciente` e adiciona novos campos.
- [ ] `V003__profissionais_credenciais.sql`: tabelas `perfis_profissionais`, `credenciais`, `disponibilidades`.
- [ ] `V004__pacientes_documentos.sql`: tabelas `pacientes`, `documentos`.
- [ ] `V005__plantoes.sql`: tabelas `plantoes`, `candidaturas_plantao`, `avaliacoes`, `repasses`.
- [ ] `V006__catalogo_equipamentos.sql`: tabelas `categorias_equipamento`, `equipamentos`, `fotos_equipamento`, `unidades_equipamento`.
- [ ] `V007__locacoes_caucoes.sql`: tabelas `locacoes`, `caucoes`, `movimentacoes_locacao`, `contratos`.
- [ ] `V008__stripe_eventos_seeds.sql`: tabela `stripe_eventos` (idempotência) + seeds de categorias.
- [ ] `V009__arquivar_legado_filmes.sql`: renomear tabelas legadas para `legacy_*` e criar novo `favoritos` polimórfico.
- [ ] `V010__contract.sql`: script de contração para execução manual futura.

### Critérios de Aceitação (DoD)
1. Migrações V001 até V009 executam sequencialmente sem erros.
2. Dados legados de usuários são preservados com nova role `familiar_paciente`.
3. Tabelas `legacy_*` preservam favoritos e comentários da P1.
4. Todos os campos monetários utilizam inteiros em centavos.
"@
    },
    @{
        Title = "feat(auth): expandir RBAC com 4 novos papéis, atributos complementares e autocadastro qualificado"
        Body = @"
### Descrição e Contexto
Evoluir o sistema de autenticação e RBAC para suportar os 4 papéis de negócio: `admin`, `profissional_saude`, `familiar_paciente` e `fornecedor_equipamento`. Mantém o Padrão A com verificação centralizada em tempo real via `/auth/verify` e blinda o autocadastro contra escalada de privilégios.

### Tarefas / Checklist de Implementação
- [ ] Atualizar schemas Pydantic em `auth_service/models.py`.
- [ ] Bloquear atribuição de `role = 'admin'` no endpoint `POST /auth/register`.
- [ ] Atualizar formulário de cadastro com seleção de perfil.
- [ ] Implementar dependências em `app/deps.py` (`require_roles`, `require_verified_professional`, `require_owner_or_admin`).
- [ ] Incluir `ator_role` nos eventos persistidos pelo `log-service`.
- [ ] Criar testes de RBAC em `tests/test_rbac.py`.

### Critérios de Aceitação (DoD)
1. Acesso anônimo a rotas privadas retorna 401 ou redireciona.
2. Acesso com papel inadequado retorna HTTP 403 Forbidden.
3. Cadastro com papel `admin` é rejeitado com HTTP 400.
4. Tentativa 403 emite evento `audit.security.access_denied`.
"@
    },
    @{
        Title = "feat(storage): reestruturar S3/Garage em 4 buckets com proxy autenticado para credenciais e laudos"
        Body = @"
### Descrição e Contexto
Organizar o storage em 4 buckets especializados (`avatars`, `equipamentos`, `credenciais`, `documentos`). Implementar proxy de streaming autenticado com validação de magic bytes e RBAC para documentos médicos e credenciais privadas.

### Tarefas / Checklist de Implementação
- [ ] Criar módulo multi-bucket `app/services/storage.py`.
- [ ] Implementar validação de magic bytes (%PDF, JPG, PNG, WEBP).
- [ ] Implementar rotas públicas `/storage/avatars/{filename}` e `/storage/equipamentos/{id}/{filename}`.
- [ ] Implementar rotas privadas `/documentos/credenciais/{id}` e `/documentos/laudos/{id}` com RBAC.
- [ ] Configurar headers de segurança (`Content-Disposition: attachment`, `nosniff`).
- [ ] Disparar evento de auditoria `documento.acessado` a cada leitura de arquivo privado.

### Critérios de Aceitação (DoD)
1. Upload de executável renomeado para `.pdf` é rejeitado na validação de magic bytes.
2. Usuário comum recebe HTTP 403 ao tentar baixar documento médico de terceiro.
3. Administrador visualiza credenciais para homologação.
"@
    },
    @{
        Title = "feat(plantoes): implementar ciclo de contratação de plantões (direto e mural) com ledger de repasses"
        Body = @"
### Descrição e Contexto
Implementar motor de contratação de plantões de cuidadores e enfermagem em duas modalidades (solicitação direta e mural emergencial sob demanda), com cobrança da diária via Stripe Checkout, retenção de take rate (12% a 15%) e ledger financeiro de repasses.

### Tarefas / Checklist de Implementação
- [ ] Implementar serviço de cálculo financeiro `app/services/pricing.py`.
- [ ] Criar endpoint `POST /plantoes/novo` (direto ou mural).
- [ ] Implementar máquina de estados com lock no aceite de plantão (`SET lock:plantao:{id} NX EX 15` + update atômico no banco).
- [ ] Integrar webhook `checkout.session.completed` (`tipo = 'plantao'`) confirmando o agendamento e registrando repasse pendente.
- [ ] Liberar repasse no check-out concluído do profissional.
- [ ] Emitir eventos de ciclo de vida no Redis Streams.

### Critérios de Aceitação (DoD)
1. Concorrência no mural: apenas 1 profissional consegue aceitar o plantão aberto.
2. Webhook marca plantão como `confirmado` e gera registro de repasse com cálculo exato de centavos.
3. Não permite check-in em plantão não pago.
"@
    },
    @{
        Title = "feat(locacoes): implementar locação de equipamentos com Stripe Billing recorrente e caução"
        Body = @"
### Descrição e Contexto
Implementar motor de locação ortopédica com faturamento mensal recorrente via Stripe Billing e pré-autorização de garantia/caução no cartão do cliente cobrindo entrega e vistoria inicial.

### Tarefas / Checklist de Implementação
- [ ] Criar script `scripts/stripe_seed_prices.py` para produtos/preços recorrentes no Stripe.
- [ ] Implementar `POST /equipamentos/{id}/locar` gerando sessão de assinatura no Stripe.
- [ ] Processar webhooks de assinatura (`checkout.session.completed`, `invoice.paid`, `customer.subscription.deleted`).
- [ ] Criar PaymentIntent de caução com `capture_method='manual'` e `off_session=True` usando o cartão salvo.
- [ ] Implementar fluxo de devolução com vistoria e cancelamento da autorização de caução.

### Critérios de Aceitação (DoD)
1. Conclusão de checkout de locação ativa assinatura e gera autorização de caução.
2. Webhook `invoice.paid` registra renovação mensal no Redis.
3. Devolução com vistoria aprovada libera a autorização de caução sem debitar o cliente.
"@
    },
    @{
        Title = "feat(events): estruturar trilha de eventos de negócio no Redis Streams e métricas de auditoria"
        Body = @"
### Descrição e Contexto
Evoluir o `log-service` para persistir eventos de domínio estruturados em Redis Streams particionados (`evt:plantao`, `evt:locacao`, `evt:pagamento`), mantendo linha do tempo e agregadores diários para o dashboard administrativo.

### Tarefas / Checklist de Implementação
- [ ] Atualizar schema `LogEvent` com campos tipados opcionais (`categoria`, `ator_role`, `entidade`, `entidade_id`, `dados`).
- [ ] Gravar em `log:eventos` e no stream específico do domínio simultaneamente.
- [ ] Manter sorted sets `idx:{entidade}:{entidade_id}` para linha do tempo.
- [ ] Atualizar contadores diários `metrics:{yyyy-mm-dd}:{acao}`.
- [ ] Implementar endpoint `GET /logs/timeline/{entidade}/{entidade_id}`.

### Critérios de Aceitação (DoD)
1. Eventos são gravados no stream mestre e no stream do domínio.
2. Consulta de linha do tempo retorna eventos ordenados por timestamp.
3. Queda do Redis não interrompe operação do usuário (best-effort mantido).
4. Dados sensíveis de saúde nunca são incluídos nos payloads do Redis.
"@
    },
    @{
        Title = "feat(ui): implementar Landing Page, Catálogo de Equipamentos e Mural de Profissionais"
        Body = @"
### Descrição e Contexto
Construir interfaces públicas da CuidaHome com design responsivo mobile-first, paleta voltada à saúde e acessibilidade WCAG AA, substituindo integralmente as views antigas de filmes.

### Tarefas / Checklist de Implementação
- [ ] Redesenhar `app/static/style.css` com design tokens de saúde.
- [ ] Atualizar `app/templates/base.html` com nova navbar contextualizada por papel e rodapé com selo FATEC.
- [ ] Implementar `app/templates/public/landing.html` com hero, vitrines e seção 'Como Funciona'.
- [ ] Implementar `app/templates/equipamentos/catalogo.html` e `detalhe.html`.
- [ ] Implementar `app/templates/profissionais/mural.html` e `detalhe.html`.

### Critérios de Aceitação (DoD)
1. Telas responsivas em desktop e mobile (375px).
2. Profissionais com status diferente de `aprovado` não aparecem na busca pública.
3. Nenhuma referência a filmes ou atores no HTML gerado.
"@
    },
    @{
        Title = "feat(ui): implementar painéis dedicados (Familiar, Profissional, Fornecedor e Admin)"
        Body = @"
### Descrição e Contexto
Construir dashboards privativos para cada um dos 4 papéis com controles específicos para gestão de escalas, estoque de equipamentos, credenciais e moderação executiva.

### Tarefas / Checklist de Implementação
- [ ] Painel Familiar (`/painel/familia`): pacientes, laudos, histórico de plantões e locações ativas.
- [ ] Painel Profissional (`/painel/profissional`): agenda, upload de credenciais e extrato de repasses.
- [ ] Painel Fornecedor (`/painel/fornecedor`): gestão de estoque, fila logística e vistorias.
- [ ] Painel Admin (`/admin`): KPIs de MRR/GMV, fila de homologação de credenciais e moderação de avaliações.

### Critérios de Aceitação (DoD)
1. Acesso aos painéis condicionado ao papel do usuário logado.
2. Upload de laudos respeita limite de 10 MB no bucket privado.
3. Homologação de credencial pelo admin libera imediatamente o profissional para atuar.
"@
    },
    @{
        Title = "ops: documentar e executar o runbook de deploy contínuo no Portainer e validação em produção"
        Body = @"
### Descrição e Contexto
Documentar e executar o procedimento operacional de atualização da stack no Portainer da FATEC (`portainer.lapps.studio`), assegurando persistência de dados, atualização de variáveis de ambiente e validação via smoke test automatizado.

### Tarefas / Checklist de Implementação
- [ ] Criar documento `docs/RUNBOOK_DEPLOY.md`.
- [ ] Criar script `scripts/smoke_test.py`.
- [ ] Documentar procedimento de backup via container `mariadb-dump`.
- [ ] Documentar atualização de variáveis de ambiente e build no Portainer.
- [ ] Documentar rollback de emergência via tag Git e restore de dump SQL.
- [ ] Executar o procedimento e anexar evidências.

### Critérios de Aceitação (DoD)
1. `docs/RUNBOOK_DEPLOY.md` versionado e completo.
2. `scripts/smoke_test.py` passando contra o domínio público.
3. Containers escutando na porta reservada 8210 via túnel FRP.
4. Dados pré-existentes de usuários preservados no MariaDB.
"@
    }
)

foreach ($issue in $issues) {
    Write-Host "Criando: $($issue.Title)..." -ForegroundColor Yellow
    gh issue create --title $issue.Title --body $issue.Body
}

Write-Host "`nTodas as 12 issues foram criadas com sucesso no GitHub!" -ForegroundColor Green

