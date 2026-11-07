# Procedimento Operacional Padrão (Runbook) — Deploy no Portainer

> **Aplicação:** CuidaHome (`saude-domiciliar`)  
> **Ambiente:** Cluster Portainer FATEC (`https://portainer.lapps.studio`)  
> **Subdomínio:** `https://iago-lima-isw055.lapps.studio`  
> **Porta Reservada Host:** `8210`  
> **Banco de Dados:** MariaDB `11.8` (`35.226.64.52:3306`)  

---

## 1. Pré-Requisitos e Preparação Local

Antes de acionar a atualização no painel do Portainer, execute os seguintes passos no seu terminal local (Windows PowerShell):

### 1.1 Criar Ponto de Restauração no Git (Tag de Rollback)
Garante que você possa reverter o código para o estado estável da P1 caso necessário:
```powershell
git tag -a v1-catalogo-filmes-final -m "Versao final estavel do catalogo de filmes (P1)"
git push origin v1-catalogo-filmes-final
```

### 1.2 Gerar Backup Lógico do MariaDB
Execute o backup lógico utilizando a imagem oficial do MariaDB em container Docker local (evitando problemas de encoding do PowerShell):
```powershell
New-Item -ItemType Directory -Force backups | Out-Null

docker run --rm -v "${PWD}/backups:/backups" mariadb:11.8 `
  mariadb-dump -h $env:DB_HOST -P $env:DB_PORT -u $env:DB_USER -p"$env:DB_PASSWORD" `
  --single-transaction --routines --triggers $env:DB_NAME `
  --result-file=/backups/backup_pre_deploy_$(Get-Date -Format yyyyMMdd_HHmm).sql
```
*Valide que o arquivo `.sql` gerado dentro de `backups/` possui tamanho superior a 0 bytes.*

---

## 2. Procedimento de Atualização no Portainer (Fluxo Docker Hub)

Como a stack no Portainer utiliza imagens pré-compiladas do Docker Hub gerenciadas pela aba **Editor (Compose Direto)**:

### 2.1 Compilar e Enviar as Imagens (Local)
No seu computador com o Docker Desktop ativo:
```powershell
.\scripts\build_and_push.ps1
```

### 2.2 Aplicar as Migrações no Banco de Dados
Como o MariaDB possui conexão direta via porta 3306:
```powershell
python -m db.migrate
```

### 2.3 Atualizar o Compose na aba Editor do Portainer
1. Acesse: `https://portainer.lapps.studio` -> Login `IAC_2026_02_iago_lima`
2. No menu lateral esquerdo, clique em **Stacks** e selecione a sua stack.
3. Clique na aba **Editor**.
4. Atualize o conteúdo do YAML colando a nova definição de serviços (sem a porta 9050 do Garage, com os 4 buckets e sem variáveis do TMDB).
5. Logo abaixo do editor de texto, ative a opção: **Re-pull image and redeploy**.
6. Clique no botão **Update the stack**.

### 2.3 Atualizar Variáveis de Ambiente no Portainer

| Variável | Ação | Valor Recomendado |
|---|---|---|
| `TMDB_API_KEY` | **Remover** | Obsoleta (não mais utilizada) |
| `STRIPE_PRICE_ID` | **Remover** | Obsoleta (preços vinculados por equipamento no banco) |
| `APP_NAME` | Adicionar | `CuidaHome` |
| `PUBLIC_BASE_URL` | Adicionar | `https://iago-lima-isw055.lapps.studio` |
| `PLATFORM_FEE_PERCENT`| Adicionar | `12` |
| `SMTP_FROM` | Atualizar | `noreply@cuidahome.com.br` |
| `SECRET_KEY` | Rotacionar | Gerar uma nova chave aleatória para invalidar sessões antigas |
| `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` | **Manter** | Credenciais originais do seu MariaDB |
| `APP_PORT` | **Manter** | `8210` (obrigatória para o roteamento do túnel FRP) |
| `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD` | **Manter** | Credenciais do Garage já configuradas |
| `GARAGE_RPC_SECRET` | **Manter** | Segredo RPC original |
| `STRIPE_API_KEY`, `STRIPE_WEBHOOK_SECRET` | **Manter** | Suas chaves de teste da Stripe |

### 2.4 Executar o Redeploy
1. Marque a caixa de seleção: **Re-pull image and redeploy** (ou *Pull latest image*).
2. Clique no botão **Update the stack**.
3. O daemon do Docker efetuará o clone do código atualizado, executará o build das imagens dos microsserviços e aplicará as migrações através do container `migrator`.

---

## 3. Validação e Healthcheck Pós-Deploy

Após a conclusão do deploy, realize as validações abaixo:

### 3.1 Status dos Containers no Portainer
Acesse a aba **Containers** e certifique-se de que os serviços estão rodando:
* `catalog-service-iago`: **healthy** (porta mapeada `8210:8000`)
* `auth-service-iago`: **healthy** (porta interna `8001`)
* `log-service-iago`: **healthy** (porta interna `8002`)
* `redis-iago`: **running** (porta interna `6379`)
* `garage-iago`: **healthy** (porta interna `9000`)
* `migrator-iago`: **exited (0)** (sucesso na execução das migrações)

### 3.2 Executar Smoke Test Automatizado
No seu terminal local, execute o script de verificação contra o subdomínio público:
```powershell
python scripts/smoke_test.py --base-url https://iago-lima-isw055.lapps.studio
```

Validações manuais no navegador:
1. Acesse `https://iago-lima-isw055.lapps.studio/`: deve carregar a Landing Page da CuidaHome.
2. Acesse `https://iago-lima-isw055.lapps.studio/catalog`: deve redirecionar (HTTP 301) para a raiz `/`.
3. Tente acessar `/painel/familia` sem estar autenticado: deve redirecionar para `/login`.

---

## 4. Plano de Rollback de Emergência

Caso ocorra alguma falha crítica impeditiva no ambiente de produção:

### 4.1 Rollback de Código (Sem perda de dados)
Como as migrações `V001` a `V009` utilizam a estratégia *expand* (aditivas e retrocompatíveis):
1. No Portainer, altere o campo **Repository reference** da stack para: `refs/tags/v1-catalogo-filmes-final`
2. Clique em **Update the stack** com **Re-pull image**.
3. O código da P1 voltará a rodar normalmente, tolerando as novas tabelas sem interrupção.

### 4.2 Rollback Total de Banco de Dados (Restauração do Dump)
Caso seja necessário restaurar o banco ao estado exato anterior ao deploy:
```powershell
docker run --rm -i -v "${PWD}/backups:/backups" mariadb:11.8 `
  mariadb -h $env:DB_HOST -P $env:DB_PORT -u $env:DB_USER -p"$env:DB_PASSWORD" $env:DB_NAME `
  < backups/backup_pre_deploy_XXXXX.sql
```

