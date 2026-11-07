# Especificação de Arquitetura Técnica — CuidaHome

> **Projeto:** CuidaHome (Saúde & Atendimento Domiciliar)  
> **Disciplina:** Introdução à Computação em Nuvem (ISW055) — FATEC  
> **Repositório:** `saude-domiciliar`  
> **Status:** Ativo / Migrado da P1  

---

## 1. Visão Geral da Arquitetura

A plataforma CuidaHome é implementada sobre uma arquitetura de **microsserviços conteinerizados** (Docker Compose) orquestrados via **Portainer CE**, mantendo comunicação por rede interna privada (`internal-net`) e expondo exclusivamente a porta pública reservada `8210`.

```
             [ Navegador / Cliente ]
                        |
                        v HTTPS (Túnel FRP - Porta 8210)
              +-------------------+
              |  catalog-service  | (Borda Pública / FastAPI)
              +----+----+----+----+
                   |    |    |
       +-----------+    |    +------------+
       | HTTP           | HTTP            | S3 API (:9000)
       v (:8001)        v (:8002)         v
+--------------+ +--------------+ +---------------+
| auth-service | | log-service  | | garage (S3)   |
+-------+------+ +-------+------+ +---------------+
        |                |
        | SQL            | Redis (:6379)
        v                v
  +-----------+    +-----------+
  |  MariaDB  |    |  redis:7  |
  +-----------+    +-----------+
```

---

## 2. Divisão dos Microsserviços e Responsabilidades

### 2.1 `catalog-service` (Gateway e Aplicação de Negócio)
* **Porta:** `8210` (no host) -> `8000` (no container).
* **Responsabilidades:**
  * Renderização Server-Side (SSR) das telas com Jinja2 e static files.
  * Catálogo de equipamentos e vitrine de profissionais certificados.
  * Gestão dos fluxos de solicitação de plantão e locação de equipamentos.
  * Integração com a Stripe (Checkout Sessions, Billing de assinaturas, pré-autorização de cauções e Webhooks).
  * Proxy de streaming autenticado para arquivos sensíveis armazenados no S3/Garage (`/documentos/*`) e proxy público de imagens (`/storage/*`).
  * Despacho de eventos de negócio assíncronos (best-effort) para o `log-service`.

### 2.2 `auth-service` (Identidade e RBAC)
* **Porta:** `8001` (apenas interna, sem exposição no host via `expose: 8001`).
* **Responsabilidades:**
  * Registro de novos usuários com 4 papéis: `familiar_paciente`, `profissional_saude`, `fornecedor_equipamento` (bloqueando autocadastro de `admin`).
  * Autenticação e emissão de tokens JWT com claims de identidade.
  * Validação centralizada de sessão e papel em tempo real (`POST /auth/verify`) consultando o banco MariaDB (Padrão A).
  * Fluxo de recuperação de senha com tokens criptográficos de uso único, validade estrita de 30 minutos e envio real de e-mails via SMTP (Mailtrap em dev).

### 2.3 `log-service` (Auditoria e Barramento de Eventos)
* **Porta:** `8002` (apenas interna, `expose: 8002`).
* **Responsabilidades:**
  * Recepção de eventos estruturados emitidos pelos demais serviços.
  * Persistência em Redis Streams particionados por domínio (`log:eventos`, `evt:plantao`, `evt:locacao`, `evt:pagamento`).
  * Manutenção de índices cronológicos (Sorted Sets) para reconstrução da linha do tempo das entidades.
  * Atualização de métricas de negócio e contadores diários via Redis Strings/Hashes.
  * Consulta protegida de auditoria restrita a administradores via JWT.

### 2.4 `garage` (Object Storage S3-Compatible)
* **Porta:** `9000` (apenas interna).
* **Responsabilidades:**
  * Armazenamento distribuído de binários com suporte ao protocolo S3.
  * Isolamento lógico em 4 buckets: `avatars`, `equipamentos`, `credenciais` e `documentos`.
  * Ausência de exposição pública de portas de administração no host para garantir segurança máxima dos laudos e documentos médicos.

---

## 3. Matriz de Controle de Acesso (RBAC)

O sistema adota o **Padrão A — Enforcement Centralizado**: a cada requisição sensível, o `catalog-service` valida o token JWT e verifica o papel atualizado do usuário consultando o banco de dados via `/auth/verify`. Além do papel, aplicam-se regras contextuais (ABAC):

| Ação do Sistema | `admin` | `profissional_saude` | `familiar_paciente` | `fornecedor_equipamento` | Visitante Anônimo |
|---|:---:|:---:|:---:|:---:|:---:|
| Ver Landing, Catálogo e Mural Público | ✅ | ✅ | ✅ | ✅ | ✅ |
| Solicitar Plantão / Pagar Diária | ❌ | ❌ | ✅ | ❌ | ❌ |
| Aceitar Plantão no Mural | ❌ | ✅ *(se aprovado)* | ❌ | ❌ | ❌ |
| Realizar Check-in / Check-out | ❌ | ✅ | ❌ | ❌ | ❌ |
| Fazer Upload de Credenciais (COREN/Diploma) | ❌ | ✅ *(próprio)* | ❌ | ✅ *(CNPJ/Alvará)* | ❌ |
| Avaliar e Aprovar Credenciais | ✅ | ❌ | ❌ | ❌ | ❌ |
| Cadastrar Equipamento e Unidades Físicas | ✅ | ❌ | ❌ | ✅ *(próprios)* | ❌ |
| Alugar Equipamento (Stripe Billing) | ❌ | ❌ | ✅ | ❌ | ❌ |
| Confirmar Despacho / Vistoria de Entrega | ✅ | ❌ | ❌ | ✅ *(própria locação)*| ❌ |
| Solicitar Devolução de Equipamento | ❌ | ❌ | ✅ *(própria locação)*| ❌ | ❌ |
| Capturar ou Liberar Caução | ✅ | ❌ | ❌ | Solicita / Admin executa | ❌ |
| Consultar Extrato de Repasses Financeiros | ✅ *(todos)* | ✅ *(próprio)* | ❌ | ✅ *(próprio)* | ❌ |
| Avaliar Atendimento pós-conclusão | ❌ | ❌ | ✅ | ❌ | ❌ |
| Acessar Painel e Logs de Auditoria | ✅ | ❌ | ❌ | ❌ | ❌ |

---

## 4. Engenharia de Dados & Migrations (Expand/Contract)

O MariaDB individual do aluno (`IAC_2026_02_iago_lima`) é gerenciado por um runner de migrações determinístico (`db/migrate.py`) que assegura a integridade transacional e a rastreabilidade via tabela `schema_migrations`.

### 4.1 Ciclo de Migração Expand/Contract

```
[ Fase Legada ]                [ Fase de Expansão (V001..V009) ]           [ Fase de Contração (V010 Manual) ]
usuarios (role VARCHAR(20))    usuarios (role VARCHAR(32))                 usuarios (CHECK in ('admin',...))
favoritos (tmdb_movie_id)  --> legacy_favoritos_filmes (arquivada)     --> DROP legacy_favoritos_filmes
comentarios (tmdb)         --> legacy_comentarios_filmes (arquivada)   --> DROP legacy_comentarios_filmes
                               novas tabelas: plantoes, locacoes, etc.
```

### 4.2 Dicionário Resumido de Novas Tabelas

1. **`usuarios`:** Ampliada com `role VARCHAR(32)`, `telefone`, `cidade`, `uf`, `ativo`.
2. **`perfis_profissionais`:** Categoria (`cuidador`, `tecnico_enfermagem`, `enfermeiro`), registro no conselho, diárias de 12h/24h em centavos, status de verificação (`pendente`, `aprovado`, `rejeitado`).
3. **`credenciais`:** Chaves de storage dos documentos enviados, MIME type, status e motivo de rejeição.
4. **`pacientes`:** Cadastro de familiares dependentes sob tutela de um familiar/cliente.
5. **`plantoes`:** Escalas de atendimento domiciliar (direta ou mural), horários, diárias, taxa de intermediação (`taxa_centavos`), valor líquido de repasse e status de ciclo de vida.
6. **`candidaturas_plantao`:** Concorrência controlada de profissionais para plantões abertos no mural.
7. **`avaliacoes`:** Notas (1 a 5) e feedbacks concedidos pelas famílias aos profissionais.
8. **`repasses`:** Ledger financeiro de repasses pendentes e liberados para prestadores de serviço e fornecedores.
9. **`categorias_equipamento`:** Classificação ortopédica (cadeiras de rodas, camas hospitalares, etc.).
10. **`equipamentos`:** Modelos disponíveis para locação, preço mensal recorrente, caução e `stripe_price_id`.
11. **`unidades_equipamento`:** Controle de patrimônio individualizado por número de série físico.
12. **`locacoes`:** Contratos de locação ativos, associados à assinatura mensal do Stripe (`stripe_subscription_id`).
13. **`caucoes`:** Pré-autorizações de cartão de crédito gerenciadas no Stripe (`capture_method=manual`).
14. **`movimentacoes_locacao`:** Rastreamento logístico de despacho, entrega, recolhimento e laudo de vistoria.
15. **`contratos`:** Histórico de aceites digitais de termos de uso e condições contratuais.
16. **`stripe_eventos`:** Registro de idempotência para processamento único de Webhooks do Stripe.

---

## 5. Estrutura do Object Storage (S3 / Garage)

| Bucket | Finalidade | Nível de Acesso | Tipo de Proxy no Gateway |
|---|---|---|---|
| `avatars` | Fotos de perfil de usuários | Leitura Pública | `/storage/avatars/{filename}` |
| `equipamentos` | Fotos e manuais de equipamentos | Leitura Pública | `/storage/equipamentos/{id}/{filename}` |
| `credenciais` | Diplomas, certidões e carteiras COREN | **Privado / Confidencial** | `/documentos/credenciais/{id}` (Dono + Admin) |
| `documentos` | Laudos médicos e vistorias de locação | **Privado / Dados Sensíveis (LGPD)** | `/documentos/laudos/{id}` (Familiar + Profissional ativo + Admin) |

---

## 6. Integração Financeira com Stripe (Modo de Teste)

### 6.1 Assinatura Recorrente com Garantia de Caução
1. O cliente escolhe o equipamento e confirma a locação.
2. O sistema gera uma Checkout Session no Stripe em `mode=subscription` associada ao `stripe_price_id` mensal do equipamento.
3. Ao receber o webhook `checkout.session.completed`, a aplicação:
   * Associa a assinatura ao contrato no banco.
   * Utiliza a forma de pagamento salva do cliente para disparar uma pré-autorização de caução (`stripe.PaymentIntent.create(capture_method='manual', off_session=True)`).
   * Registra a caução com a data limite de captura informada pela bandeira (`capture_before`).
4. Durante os primeiros 7 dias (despacho e vistoria inicial), a garantia opera com fundos retidos. Após isso, opera com o cartão salvo em contrato para cobrança de eventuais danos na devolução.

### 6.2 Intermediação de Plantões (Take Rate)
1. O familiar solicita ou confirma um cuidador para o plantão.
2. O pagamento é realizado via Stripe Checkout (`mode=payment`) cobrando a diária cheia.
3. A taxa de intermediação (`PLATFORM_FEE_PERCENT = 12%`) é automaticamente calculada e separada.
4. O valor líquido é lançado no ledger `repasses` e liberado após o check-out do profissional.

