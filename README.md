# CuidaHome — Saúde & Atendimento Domiciliar

> **Disciplina:** Introdução à Computação em Nuvem (ISW055) — 2026.2  
> **Docente:** Prof. Allan Siriani ([github.com/siriani](https://github.com/siriani) / `@siriani`)  
> **Aluno:** Iago Amorim Lebron de Lima (RA: 2591612513019)  
> **Repositório de Origem (Evidência P1):** [github.com/Lebron057/tom-hanks-avestruz](https://github.com/Lebron057/tom-hanks-avestruz)  
> **Repositório Atual (SaaS / Atividade 9):** [github.com/Lebron057/saude-domiciliar](https://github.com/Lebron057/saude-domiciliar)  
> **Subdomínio Público (Portainer):** [https://iago-lima-isw055.lapps.studio](https://iago-lima-isw055.lapps.studio) (Porta `8210`)

---

## 1. Nome e Frase de Impacto

* **Nome do Produto:** **CuidaHome** (*Saúde & Atendimento Domiciliar*)
* **Frase:** *Plataforma integrada de plantões de cuidadores/enfermagem sob demanda e locação desburocratizada de equipamentos hospitalares para recuperação domiciliar.*

---

## 2. A Dor

* **Quem sofre:** Familiares de idosos, responsáveis por pacientes pós-alta cirúrgica e pacientes em recuperação temporária que necessitam de cuidados assistenciais ou suporte ortopédico imediato.
* **Quando:** Imediatamente após uma alta hospitalar inesperada, no desfalque súbito de um cuidador habitual durante finais de semana/feriados ou após traumas ortopédicos graves (ex: fraturas de fêmur, cirurgias de joelho).
* **Quanto custa hoje:** 
  * Risco severo de reinternação hospitalar por assistência inadequada.
  * Perda de dias úteis e produtividade de familiares dedicados ao cuidado informal.
  * Desembolso de R\$ 2.000,00 a R\$ 5.000,00 na aquisição de camas hospitalares ou cadeiras de rodas que serão utilizadas por apenas 60 a 90 dias.
  * Horas de estresse em grupos de WhatsApp sem qualquer garantia técnica, validação de certidões ou amparo jurídico.
* **Como resolvem hoje:** Grupos informais de WhatsApp e redes sociais, indicações boca a boca de vizinhos e lojas físicas especializadas em locação ortopédica que impõem burocracias arcaicas (exigência de fiador, promissórias ou cauções presenciais em dinheiro/cheque).

---

## 3. Persona

* **Nome:** Mariana Lopes, 43 anos, bancária e mãe.
* **Rotina e Obstáculo:** A mãe de Mariana (Dona Helena, 78 anos) sofreu uma queda em casa e passou por cirurgia de urgência no fêmur. Recebeu alta hospitalar de surpresa na sexta-feira à tarde. Mariana trabalha em horário integral, reside em outra localidade e precisa contratar com extrema urgência cuidadores/técnicos de enfermagem certificados para plantões noturnos e de fins de semana, além de providenciar uma cama hospitalar articulada e uma cadeira de rodas adaptada para a mesma semana. Enfrenta a lentidão das lojas tradicionais de locação e o pânico de colocar pessoas desconhecidas sem antecedentes ou qualificação verificada dentro da residência da mãe.

---

## 4. Concorrentes e Alternativas

1. **Grupos de WhatsApp e Classificados Informais:**
   * *Limitações:* Ausência absoluta de triagem de antecedentes criminais ou verificação ativa de registros profissionais (COREN); elevado índice de cancelamento de última hora e pagamentos sem emissão de comprovantes fiscais ou respaldo jurídico.
2. **Lojas Físicas Tradicionais de Locação Ortopédica:**
   * *Limitações:* Obrigatoriedade de deslocamento presencial no horário comercial, processos analógicos com assinatura física de contratos, exigência abusiva de fiadores ou cauções em dinheiro/cheque e falta de entrega/recolhimento ágil em domicílio.
3. **Agências Tradicionais de Home Care:**
   * *Limitações:* Foco predominante em contratos de alta complexidade contínua e planos de saúde corporativos; rigidez de contratação, custos exorbitantes de intermediação e nenhuma flexibilidade para plantões avulsos de curta duração ou demandas pontuais de fim de semana.

---

## 5. Proposta de Valor

> **Conectamos famílias a cuidadores certificados em minutos e entregamos equipamentos ortopédicos por assinatura flexível e sem caução burocrática.**

Garantimos validação prévia de credenciais (diplomas e COREN), agilidade no atendimento emergencial (mural sob demanda), facilidade de contratação via Stripe Checkout em poucos cliques e entrega/recolhimento ágil de equipamentos médicos no domicílio do paciente.

---

## 6. Modelo de Receita com Stripe

A plataforma opera com duas linhas de monetização complementares, integradas ao Stripe em modo de teste:

1. **Intermediação de Plantões (Take Rate):**
   * Cobrança avulsa realizada através do Stripe Checkout (`mode=payment`) no fechamento do plantão.
   * Retenção de taxa de intermediação de **12%** a **15%** (configurada via `PLATFORM_FEE_PERCENT`) sobre a diária acordada com o profissional, direcionando o saldo líquido para o ledger financeiro de repasses do prestador.
2. **Plano Recorrente de Locação de Equipamentos (Stripe Billing):**
   * Assinatura mensal automatizada via Stripe Billing (`mode=subscription`): ex: R\$ 149,00/mês para cadeira de rodas padrão; R\$ 290,00/mês para cama hospitalar articulada.
   * Faturamento renovado a cada ciclo de 30 dias até a solicitação de devolução pelo cliente.
   * **Garantia Patrimonial:** Pré-autorização temporária de caução no cartão do cliente (`capture_method=manual`) cobrindo o período de entrega e vistoria inicial, aliada à guarda do meio de pagamento seguro para cobranças de eventuais avarias contratuais na devolução.

---

## 7. Métricas de Sucesso

| Métrica | Meta / Indicador | Finalidade |
|---|---|---|
| **MRR (Monthly Recurring Revenue)** | Crescimento contínuo de receita recorrente | Medir o volume e a expansão de assinaturas ativas de locação de equipamentos. |
| **GMV & Take Rate** | Volume total transacionado e margem retida | Avaliar o montante bruto transacionado em plantões e a receita líquida retida pela intermediação (12–15%). |
| **Tempo de Atendimento (Match Time)** | **< 2 horas** entre solicitação e match confirmado | Garantir a eficácia e a agilidade da plataforma em situações emergenciais pós-alta. |
| **Retenção & Churn de Equipamentos** | Ciclo médio de **60 a 90 dias** com devolução programada | Acompanhar a permanência do paciente em recuperação sem retenção de itens inativos. |

---

## 8. Lean Canvas

| Bloco | Aplicação no CuidaHome (`saude-domiciliar`) |
| :--- | :--- |
| **Problema** | 1. Dificuldade crítica de encontrar cuidadores e enfermagem de confiança para plantões pontuais ou emergenciais.<br>2. Burocracia excessiva, exigência de fiador/cheque e alto custo para locação de aparelhos ortopédicos por curtos períodos. |
| **Segmentos de Clientes** | • Filhos e familiares responsáveis por idosos ou dependentes.<br>• Pacientes adultos em recuperação pós-cirúrgica ou pós-trauma temporário.<br>• Profissionais autônomos de enfermagem e cuidadores de idosos qualificados.<br>• Lojas fornecedoras de equipamentos ortopédicos. |
| **Proposta Única de Valor** | Confiabilidade imediata em cuidadores verificados e aluguel de aparelhos médicos em poucos cliques, sem fiador nem cheque, com entrega domiciliar. |
| **Solução** | 1. Plataforma web com cadastro e verificação ativa de credenciais de cuidadores/enfermeiros.<br>2. Catálogo virtual de locação mensal de equipamentos hospitalares.<br>3. Pagamentos e garantias 100% integrados via Stripe. |
| **Canais** | Parcerias estratégicas com clínicas de fisioterapia e ortopedia, hospitais pós-alta, tráfego local patrocinado (Google Ads) e recomendações boca a boca. |
| **Fontes de Receita** | • Taxa de intermediação (12% a 15%) sobre plantões de saúde intermediados.<br>• Assinaturas recorrentes mensais de locação de equipamentos (Stripe Billing). |
| **Estrutura de Custos** | • Custos de infraestrutura de nuvem e servidores (Portainer/MariaDB/Redis/S3).<br>• Taxas de processamento financeiro (Stripe).<br>• Custos de checagem documental e certidões.<br>• Logística de transporte e higienização/revisão dos aparelhos. |
| **Métricas-Chave** | Número de plantões realizados/mês, MRR de equipamentos, tempo médio de match (< 2h) e taxa de pontualidade/avaliação média (NPS). |
| **Vantagem Injusta** | Rede de cuidadores e enfermeiros pré-credenciados localmente com checagem de conselho (COREN) e processo de locação 100% digital e desburocratizado. |

---

## 9. Mapa de Reaproveitamento de Arquitetura

Conforme as diretrizes da disciplina, a infraestrutura, os microsserviços e as integrações originais foram 100% preservados e transpostos semanticamente para o novo domínio:

| Componente Anterior | Destino no CuidaHome (`saude-domiciliar`) | Aplicação Técnica no Domínio de Saúde |
|---|---|---|
| **Catálogo de Filmes (TMDB API)** | **Catálogo de Equipamentos e Mural de Profissionais** | Catálogo persistido de aparelhos ortopédicos (cadeiras, camas) e mural de busca sob demanda de plantonistas certificados. |
| **Login & RBAC (`auth-service`)** | **Matriz de Acesso RBAC Especializada** | 4 novos papéis: `admin`, `profissional_saude`, `familiar_paciente` e `fornecedor_equipamento`, com enforcement centralizado e proteção IDOR. |
| **Logs de Auditoria (`log-service` + Redis)** | **Trilha de Auditoria e Eventos de Negócio** | Eventos estruturados em Redis Streams: `"plantao.solicitado"`, `"plantao.confirmado"`, `"equipamento.despachado"`, `"locacao.renovada"`. |
| **Upload de Perfil (`garage`/MinIO S3)** | **Object Storage Especializado (4 Buckets)** | Buckets `avatars` (público), `equipamentos` (fotos públicas), `credenciais` (COREN/diplomas privados) e `documentos` (laudos/termos privados). |
| **Plano Premium (Stripe)** | **Assinaturas Recorrentes & Cobrança de Plantões** | Cobrança mensal da locação ortopédica (Stripe Billing) com caução via pré-autorização e checkout de plantões avulsos com split de taxa. |
| **Orquestração Docker & Portainer** | **Stack Portainer Multi-Tenant (Porta `8210`)** | Mesma stack Docker Compose na porta reservada `8210`, túnel reverso FRP, MariaDB individual e volumes persistentes preservados. |

---

## 10. Arquitetura Técnica e Microsserviços

```
                     [ CLIENTES / INTERNET ]
                                |
                                v  HTTPS: https://iago-lima-isw055.lapps.studio
             +---------------------------------------+
             | GCP e2-micro (Always Free Relay FRP)  |
             +------------------+--------------------+
                                | Túnel TCP Reverso (Porta 8210)
                                v
====================================================================
           AMBIENTE ON-PREMISES / PORTAINER (HOST DO ALUNO)
====================================================================
  +---------------------------------------------------------------+
  |  catalog-service (FastAPI - Porta Pública: 8210)              |
  |  - Landing Page, Catálogo Ortopédico, Mural de Plantões       |
  |  - Proxies autenticados para S3 e Checkout Stripe             |
  +--------+------------------+-------------------+---------------+
           |                  |                   |
           | HTTP             | HTTP              | S3 API (Porta 9000)
           v (:8001)          v (:8002)           v
  +-----------------+  +-----------------+  +---------------------+
  |  auth-service   |  |   log-service   |  |   garage (MinIO S3) |
  |  (FastAPI/JWT)  |  |   (FastAPI)     |  |   Buckets:          |
  |  - RBAC 4 Roles |  +--------+--------+  |   - avatars         |
  |  - Reset Senha  |           | Redis     |   - equipamentos    |
  +--------+--------+           v (:6379)   |   - credenciais     |
           |           +-----------------+  |   - documentos      |
           |           |   redis:7       |  +----------+----------+
           |           +-----------------+             |
           | MariaDB (:3306)                           | Volumes Locais
           v                                           v
  +---------------------------------------------------------------+
  |  MariaDB Compartilhado FATEC (Banco: IAC_2026_02_iago_lima)    |
  |  - Tabelas de Saúde, Plantões, Locações, Ledger e Migrations  |
  +---------------------------------------------------------------+
```

---

## 11. Como Rodar Localmente

### 1. Clonar o repositório
```bash
git clone https://github.com/Lebron057/saude-domiciliar.git
cd saude-domiciliar
```

### 2. Configurar variáveis de ambiente
Copie o template de desenvolvimento e preencha suas chaves (Stripe, banco, secret):
```bash
cp .env.example .env
```

### 3. Subir os microsserviços via Docker Compose
```bash
docker compose up -d --build
```

O compose executa automaticamente o serviço `migrator` aplicando todas as migrações versionadas pendentes no MariaDB antes de iniciar o `catalog-service` e o `auth-service`.

Acesse no navegador:
* **Aplicação Web:** `http://localhost:8210`
* **Healthcheck do Sistema:** `http://localhost:8210/health`
* **Mural de Plantões:** `http://localhost:8210/profissionais`
* **Catálogo de Equipamentos:** `http://localhost:8210/equipamentos`

---

## 12. Documentação Complementar e Backlog

* [Arquitetura Detalhada do Sistema](docs/ARQUITETURA_SAUDE_DOMICILIAR.md)
* [Runbook de Deploy no Portainer](docs/RUNBOOK_DEPLOY.md)
* [Backlog de Issues do GitHub (12 Issues Detalhadas)](docs/backlog/ISSUES.md)
* [Documentação da P1 e Arquivos Legados de Filmes](docs/legado/DOCUMENTACAO.md)
