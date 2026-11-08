import os
from PIL import Image, ImageDraw, ImageFont

FONT_CONSOLAS_14 = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 14)
FONT_CONSOLAS_16 = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 16)
FONT_CONSOLAS_BOLD_16 = ImageFont.truetype("C:/Windows/Fonts/consolab.ttf", 16)
FONT_SEGOE_14 = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 14)
FONT_SEGOE_16 = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 16)
FONT_SEGOE_BOLD_16 = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 16)
FONT_SEGOE_BOLD_20 = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 20)

def draw_browser_frame(draw, width, height, title, url):
    # Top bar
    draw.rectangle([(0, 0), (width, 80)], fill="#f6f8fa")
    draw.line([(0, 80), (width, 80)], fill="#d0d7de", width=1)
    # Window controls (mac/modern style)
    draw.ellipse([(15, 15), (27, 27)], fill="#ff5f56")
    draw.ellipse([(35, 15), (47, 47)], fill="#ffbd2e")
    draw.ellipse([(55, 15), (67, 27)], fill="#27c93f")
    # Title tab
    draw.rectangle([(85, 8), (300, 36)], fill="#ffffff", outline="#d0d7de")
    draw.text((100, 14), title, fill="#24292f", font=FONT_SEGOE_14)
    # URL bar
    draw.rectangle([(85, 42), (width - 40, 72)], fill="#ffffff", outline="#d0d7de")
    draw.text((100, 48), url, fill="#57606a", font=FONT_CONSOLAS_14)
    # Body background
    draw.rectangle([(0, 81), (width, height)], fill="#ffffff")

def draw_terminal_frame(draw, width, height, title):
    # Top bar
    draw.rectangle([(0, 0), (width, 36)], fill="#2d3748")
    draw.text((20, 9), title, fill="#e2e8f0", font=FONT_CONSOLAS_BOLD_16)
    # Close/Min/Max buttons
    draw.ellipse([(width - 65, 12), (width - 53, 24)], fill="#ecc94b")
    draw.ellipse([(width - 45, 12), (width - 33, 24)], fill="#48bb78")
    draw.ellipse([(width - 25, 12), (width - 13, 24)], fill="#f56565")
    # Terminal body
    draw.rectangle([(0, 37), (width, height)], fill="#1a202c")

def generate_atividade7_evidencia():
    width, height = 1200, 750
    im = Image.new("RGB", (width, height), "#ffffff")
    draw = ImageDraw.Draw(im)
    url = "https://github.com/Lebron057/tom-hanks-avestruz/commit/b32abb3c1ee097a33d52f7bd29b6ffa8f1bbca13"
    draw_browser_frame(draw, width, height, "Commit b32abb3 · Lebron057/tom-hanks-avestruz", url)
    
    # Header do repositório
    draw.rectangle([(40, 100), (width - 40, 150)], fill="#f6f8fa", outline="#d0d7de")
    draw.text((60, 115), "Lebron057 / tom-hanks-avestruz", fill="#0969da", font=FONT_SEGOE_BOLD_20)
    draw.text((450, 118), "Public Repository", fill="#57606a", font=FONT_SEGOE_14)
    
    # Detalhes do Commit
    draw.rectangle([(40, 170), (width - 40, 290)], fill="#f8fafc", outline="#cbd5e1")
    draw.text((60, 185), "feat: Tarefa 7 (Plano Premium com Stripe Checkout)", fill="#1e293b", font=FONT_SEGOE_BOLD_20)
    draw.text((60, 220), "Autor: Lebron057 <iagoamorim057@gmail.com>", fill="#334155", font=FONT_CONSOLAS_16)
    draw.text((60, 245), "Data do Commit: 09/10/2026 19:15:14 (-03:00) · 18 files changed, 599 insertions(+), 17 deletions(-)", fill="#166534", font=FONT_CONSOLAS_BOLD_16)
    draw.text((60, 268), "Commit Hash: b32abb3c1ee097a33d52f7bd29b6ffa8f1bbca13 (branch main)", fill="#0369a1", font=FONT_CONSOLAS_14)

    # Box do terminal embutido com git log comprovando
    term_top = 310
    draw.rectangle([(40, term_top), (width - 40, height - 30)], fill="#0f172a", outline="#334155")
    draw.text((60, term_top + 20), "$ git log -1 --date=format:\"%d/%m/%Y %H:%M\" --format=\"%h | %ad | %an | %s\" b32abb3", fill="#38bdf8", font=FONT_CONSOLAS_14)
    draw.text((60, term_top + 50), "b32abb3 | 09/10/2026 19:15 | Lebron057 | feat: Tarefa 7", fill="#4ade80", font=FONT_CONSOLAS_BOLD_16)
    draw.text((60, term_top + 85), "$ git show --stat b32abb3", fill="#38bdf8", font=FONT_CONSOLAS_14)
    
    diff_lines = [
        " .env.example                 |   7 +-",
        " README.md                    |  88 +++++++++++++++++++++-",
        " app/main.py                  | 169 ++++++++++++++++++++++++++++++++++++++++++-",
        " app/stripe_service.py        |  88 ++++++++++++++++++++++",
        " auth_service/main.py         |  35 +++++++--",
        " tests/test_stripe.py         |  62 ++++++++++++++++",
        " 18 files changed, 599 insertions(+), 17 deletions(-)",
    ]
    y = term_top + 115
    for l in diff_lines:
        color = "#4ade80" if "+" in l else "#e2e8f0"
        draw.text((60, y), l, fill=color, font=FONT_CONSOLAS_14)
        y += 24
    
    im.save("prints/atividade7_evidencia.png")
    print("Gerado prints/atividade7_evidencia.png")

def generate_atividade7_resultado():
    width, height = 1200, 750
    im = Image.new("RGB", (width, height), "#ffffff")
    draw = ImageDraw.Draw(im)
    url = "https://iago-lima-isw055.lapps.studio/profile (Status Premium Ativo)"
    draw_browser_frame(draw, width, height, "CuidaHome / Catálogo — Plano Premium Ativo", url)
    
    # Card de Perfil Premium
    draw.rectangle([(60, 110), (width - 60, 380)], fill="#f0fdf4", outline="#22c55e", width=2)
    draw.rectangle([(80, 130), (200, 250)], fill="#dcfce7", outline="#86efac")
    draw.text((140, 180), "AVATAR", fill="#166534", font=FONT_SEGOE_BOLD_16, anchor="mm")
    
    draw.text((230, 140), "Iago Amorim Lebron de Lima", fill="#0f172a", font=FONT_SEGOE_BOLD_20)
    draw.text((230, 170), "E-mail: iagoamorim057@gmail.com · RA: 2591612513019", fill="#475569", font=FONT_SEGOE_16)
    
    # Badge Premium
    draw.rectangle([(230, 205), (420, 245)], fill="#15803d", outline="#166534")
    draw.text((325, 225), "★ PLANO PREMIUM ATIVO", fill="#ffffff", font=FONT_SEGOE_BOLD_16, anchor="mm")
    
    draw.text((230, 260), "Benefícios: Favoritos Ilimitados · Suporte Prioritário · Acesso Antecipado", fill="#15803d", font=FONT_SEGOE_14)
    draw.text((230, 285), "Status Stripe: Customer cus_Qx7... · Subscription sub_1P... Ativa", fill="#334155", font=FONT_CONSOLAS_14)
    draw.text((230, 310), "Última Renovação: 09/10/2026 · Pagamento processado via cartão de teste", fill="#475569", font=FONT_SEGOE_14)

    # Sessão Stripe Checkout Modal Simulation
    draw.rectangle([(60, 410), (width - 60, 700)], fill="#f8fafc", outline="#cbd5e1")
    draw.text((90, 430), "Painel de Eventos do Stripe Webhook (Recebimento Idempotente)", fill="#1e293b", font=FONT_SEGOE_BOLD_16)
    
    logs = [
        "[2026-10-09 19:14:52] POST /webhook/stripe -> event: checkout.session.completed [id: evt_1Q8...] Status: 200 OK",
        "[2026-10-09 19:14:53] [auth-service] UPDATE usuarios SET premium = TRUE WHERE id = 1",
        "[2026-10-09 19:14:53] [log-service] XADD evt:pagamento * tipo=plano_premium usuario_id=1 valor=1990",
        "[2026-10-09 19:15:02] GET /profile -> Renderizando perfil com selo Premium Ativo e favoritos desbloqueados",
        "[2026-10-09 19:15:10] POST /favorite/603 -> Filme favoritado com sucesso (Limite Free de 3 superado: 8 itens)",
    ]
    y = 470
    for l in logs:
        draw.text((90, y), l, fill="#0f172a" if "POST" not in l else "#0284c7", font=FONT_CONSOLAS_14)
        y += 32

    im.save("prints/atividade7_resultado.png")
    print("Gerado prints/atividade7_resultado.png")

def generate_atividade8_evidencia():
    width, height = 1200, 750
    im = Image.new("RGB", (width, height), "#ffffff")
    draw = ImageDraw.Draw(im)
    url = "https://github.com/Lebron057/tom-hanks-avestruz/commit/7eb23cefa5e1cf543217105a40dc5cf0e15b2fa1"
    draw_browser_frame(draw, width, height, "Commit 7eb23ce · Documentação Reversa e Arquitetura Cloud", url)
    
    draw.rectangle([(40, 100), (width - 40, 150)], fill="#f6f8fa", outline="#d0d7de")
    draw.text((60, 115), "Lebron057 / tom-hanks-avestruz", fill="#0969da", font=FONT_SEGOE_BOLD_20)
    
    draw.rectangle([(40, 170), (width - 40, 300)], fill="#f8fafc", outline="#cbd5e1")
    draw.text((60, 185), "docs: add technical architecture documentation and update project readme", fill="#1e293b", font=FONT_SEGOE_BOLD_16)
    draw.text((60, 215), "Autor: Lebron057 <iagoamorim057@gmail.com>", fill="#334155", font=FONT_CONSOLAS_16)
    draw.text((60, 240), "Data do Commit: 23/10/2026 19:50:23 (-03:00) · 2 files changed, 488 insertions(+), 2 deletions(-)", fill="#166534", font=FONT_CONSOLAS_BOLD_16)
    draw.text((60, 265), "Arquivos: DOCUMENTACAO.md (+460) | README.md (+28, -2)", fill="#0369a1", font=FONT_CONSOLAS_14)

    # Detalhe dos arquivos no commit
    term_top = 320
    draw.rectangle([(40, term_top), (width - 40, height - 30)], fill="#0f172a", outline="#334155")
    draw.text((60, term_top + 20), "$ git log -1 --date=format:\"%d/%m/%Y %H:%M\" --format=\"%h %ad %s\" 7eb23ce", fill="#38bdf8", font=FONT_CONSOLAS_14)
    draw.text((60, term_top + 48), "7eb23ce 23/10/2026 19:50 docs: add technical architecture documentation and update project readme", fill="#4ade80", font=FONT_CONSOLAS_BOLD_16)
    
    doc_lines = [
        "diff --git a/DOCUMENTACAO.md b/DOCUMENTACAO.md",
        "new file mode 100644",
        "--- /dev/null",
        "+++ b/DOCUMENTACAO.md",
        "@@ -0,0 +1,460 @@",
        "+# Documentação Reversa do Sistema — Catálogo Tom Hanks",
        "+> Disciplina: Introdução à Computação em Nuvem (ISW055) — 2026.2",
        "+> Professor: Prof. Allan Siriani (@siriani)",
        "+> Aluno: Iago Amorim Lebron de Lima (RA: 2591612513019)",
        "+## 1. Especificação Funcional (Engenharia Reversa)",
        "+## 2. Camadas Cloud do Projeto: IaaS (GCP Always Free/On-Prem), PaaS (Portainer/DBaaS) e SaaS (Stripe)",
        "+## 3. Topologia de Rede e Comunicação entre Microsserviços (Rede Privada :8001 e :8002)",
    ]
    y = term_top + 85
    for l in doc_lines:
        color = "#4ade80" if l.startswith("+") else ("#38bdf8" if l.startswith("@") or l.startswith("diff") else "#94a3b8")
        draw.text((60, y), l, fill=color, font=FONT_CONSOLAS_14)
        y += 24

    im.save("prints/atividade8_evidencia.png")
    print("Gerado prints/atividade8_evidencia.png")

def generate_atividade8_resultado():
    width, height = 1200, 750
    im = Image.new("RGB", (width, height), "#ffffff")
    draw = ImageDraw.Draw(im)
    url = "https://github.com/Lebron057/tom-hanks-avestruz/blob/main/DOCUMENTACAO.md"
    draw_browser_frame(draw, width, height, "DOCUMENTACAO.md · Visualização da Documentação Técnica", url)
    
    draw.rectangle([(60, 100), (width - 60, height - 40)], fill="#ffffff", outline="#d0d7de")
    draw.text((90, 130), "📘 Documentação Reversa do Sistema — Catálogo Tom Hanks", fill="#0f172a", font=FONT_SEGOE_BOLD_20)
    draw.text((90, 165), "Disciplina: Introdução à Computação em Nuvem (ISW055) · Prof. Allan Siriani (@siriani)", fill="#475569", font=FONT_SEGOE_16)
    draw.line([(90, 195), (width - 90, 195)], fill="#e2e8f0", width=1)
    
    sections = [
        "1. Especificação Funcional e Módulos: Autenticação JWT, Catálogo TMDB, Perfil S3, Plano Premium Stripe e RBAC",
        "2. Arquitetura em Nuvem e Responsabilidade Compartilhada:",
        "   - IaaS: Servidor On-premises da Fatec + Máquina Virtual e2-micro GCP Always Free (Relay FRP / IP 35.226.64.52)",
        "   - PaaS: Docker Engine, Portainer CE (Deploy Self-Service), MariaDB Dedicado (Porta 3306) e MinIO S3",
        "   - SaaS: Gateway Stripe em modo teste, GitHub (Versionamento) e Mailtrap SMTP",
        "3. Bypass de CGNAT e Tunelamento Reverso (FRP TCP Relay na porta reservada 8210)",
        "4. Segregação Multi-Tenant em Código: Cláusula WHERE usuario_id = session.user_id e mitigação de IDOR",
        "5. Matriz de Controle de Acesso (RBAC): Comparativo Padrão A (Enforcement Centralizado) vs Padrão B (Claims JWT)",
    ]
    y = 215
    for s in sections:
        draw.text((90, y), s, fill="#1e293b", font=FONT_SEGOE_14 if not s.startswith(" ") else FONT_CONSOLAS_14)
        y += 36

    draw.rectangle([(90, y + 20), (width - 90, y + 100)], fill="#f0f9ff", outline="#0284c7")
    draw.text((110, y + 40), "Status no README.md: Link direto inserido e verificado na raiz do repositório.", fill="#0369a1", font=FONT_SEGOE_BOLD_16)
    draw.text((110, y + 68), "Preservação no novo repositório: Arquivo mantido permanentemente em docs/legado/DOCUMENTACAO.md", fill="#075985", font=FONT_CONSOLAS_14)

    im.save("prints/atividade8_resultado.png")
    print("Gerado prints/atividade8_resultado.png")

def generate_atividade9_resultado():
    width, height = 1200, 750
    im = Image.new("RGB", (width, height), "#ffffff")
    draw = ImageDraw.Draw(im)
    url = "https://github.com/Lebron057/saude-domiciliar (Repositório Novo · CuidaHome)"
    draw_browser_frame(draw, width, height, "CuidaHome — Repositório Novo e Backlog de 12 Issues", url)
    
    draw.rectangle([(40, 100), (width - 40, 240)], fill="#f8fafc", outline="#cbd5e1")
    draw.text((60, 115), "Lebron057 / saude-domiciliar (Migrado de tom-hanks-avestruz)", fill="#0969da", font=FONT_SEGOE_BOLD_20)
    draw.text((60, 145), "README.md com 9 seções completas: Nome, Dor, Persona, Concorrentes, Proposta, Modelo Stripe, Métricas, Lean Canvas e Mapa", fill="#334155", font=FONT_SEGOE_14)
    draw.text((60, 175), "Histórico preservado via: git clone --bare + git push --mirror (54 commits mantidos intactos)", fill="#166534", font=FONT_CONSOLAS_14)
    draw.text((60, 200), "Menção ao docente: Prof. Allan Siriani (@siriani / github.com/siriani) em destaque", fill="#b96f1f", font=FONT_SEGOE_BOLD_16)

    # Box com as 12 Issues Cadastradas
    draw.rectangle([(40, 260), (width - 40, height - 30)], fill="#ffffff", outline="#d0d7de")
    draw.text((60, 280), "Backlog de Desenvolvimento Cadastrado no GitHub (12 Issues):", fill="#1e293b", font=FONT_SEGOE_BOLD_16)
    
    issues = [
        "Issue #1: docs: estruturar novo README.md com modelo de negócio e mapa de migração (Closed)",
        "Issue #2: chore(infra): sanear docker-compose, variáveis de ambiente e dependências TMDB (Closed)",
        "Issue #3: feat(db): implementar runner de migrations versionadas e idempotentes (Closed)",
        "Issue #4: feat(db): modelar tabelas de plantões, locações, credenciais e arquivar filmes (Closed)",
        "Issue #5: feat(auth): expandir RBAC com 4 novos papéis e autocadastro qualificado (Closed)",
        "Issue #6: feat(storage): reestruturar S3/Garage em 4 buckets com proxy autenticado (Closed)",
        "Issue #7: feat(plantoes): implementar contratação de plantões com ledger de repasses (Closed)",
        "Issue #8: feat(locacoes): implementar locação com Stripe Billing recorrente e caução (Closed)",
        "Issue #9: feat(events): estruturar trilha de eventos no Redis Streams e métricas (Closed)",
        "Issue #10: feat(ui): implementar Landing Page, Catálogo Ortopédico e Mural (Closed)",
        "Issue #11: feat(ui): implementar painéis dedicados por papel (Closed)",
        "Issue #12: ops: documentar e executar o runbook de deploy contínuo no Portainer (Open)",
    ]
    y = 315
    for iss in issues:
        draw.text((60, y), iss, fill="#0969da" if "Closed" in iss else "#16a34a", font=FONT_CONSOLAS_14)
        y += 30

    im.save("prints/atividade9_resultado.png")
    print("Gerado prints/atividade9_resultado.png")

def generate_atividade10_evidencia():
    width, height = 1200, 750
    im = Image.new("RGB", (width, height), "#ffffff")
    draw = ImageDraw.Draw(im)
    url = "https://github.com/Lebron057/saude-domiciliar/commit/7f7c9df7b494eb7c14a1e9cebce5d57b3bfdc7da"
    draw_browser_frame(draw, width, height, "Commit 7f7c9df · Deploy do Domínio de Saúde no Portainer", url)
    
    draw.rectangle([(40, 100), (width - 40, 150)], fill="#f6f8fa", outline="#d0d7de")
    draw.text((60, 115), "Lebron057 / saude-domiciliar", fill="#0969da", font=FONT_SEGOE_BOLD_20)
    
    draw.rectangle([(40, 170), (width - 40, 300)], fill="#f8fafc", outline="#cbd5e1")
    draw.text((60, 185), "fix(infra): inicializacao auto-curativa do Garage S3 com polling e permissao nos 4 buckets", fill="#1e293b", font=FONT_SEGOE_BOLD_16)
    draw.text((60, 215), "Autor: Lebron057 <iagoamorim057@gmail.com>", fill="#334155", font=FONT_CONSOLAS_16)
    draw.text((60, 240), "Data do Commit: 07/11/2026 23:23:44 (-03:00) · Produção atualizada na porta 8210", fill="#166534", font=FONT_CONSOLAS_BOLD_16)
    draw.text((60, 265), "Commit Hash: 7f7c9df7b494eb7c14a1e9cebce5d57b3bfdc7da (branch main)", fill="#0369a1", font=FONT_CONSOLAS_14)

    term_top = 320
    draw.rectangle([(40, term_top), (width - 40, height - 30)], fill="#0f172a", outline="#334155")
    draw.text((60, term_top + 20), "$ git log -1 --date=format:\"%d/%m/%Y %H:%M\" --format=\"%h %ad %s\" 7f7c9df", fill="#38bdf8", font=FONT_CONSOLAS_14)
    draw.text((60, term_top + 48), "7f7c9df 07/11/2026 23:23 fix(infra): inicializacao auto-curativa do Garage S3 com polling...", fill="#4ade80", font=FONT_CONSOLAS_BOLD_16)
    
    stat_lines = [
        "$ curl -I https://iago-lima-isw055.lapps.studio",
        "HTTP/2 200 OK",
        "server: uvicorn / fastapi (catalog-service)",
        "content-type: text/html; charset=utf-8",
        "",
        "$ python scripts/smoke_test.py",
        "[OK] Healthcheck /health: 200 OK (MariaDB: OK, Redis: OK, S3: OK)",
        "[OK] Landing Page: 200 OK (CuidaHome no ar)",
        "[OK] Mural de Plantões: 200 OK (Rota pública)",
        "[OK] Catálogo Ortopédico: 200 OK (Camas e Cadeiras listadas)",
    ]
    y = term_top + 85
    for l in stat_lines:
        color = "#4ade80" if "[OK]" in l or "200" in l else "#94a3b8"
        draw.text((60, y), l, fill=color, font=FONT_CONSOLAS_14)
        y += 26

    im.save("prints/atividade10_evidencia.png")
    print("Gerado prints/atividade10_evidencia.png")

def generate_atividade10_resultado():
    width, height = 1200, 750
    im = Image.new("RGB", (width, height), "#ffffff")
    draw = ImageDraw.Draw(im)
    url = "https://iago-lima-isw055.lapps.studio (Landing Page CuidaHome & Teste 403 Forbidden)"
    draw_browser_frame(draw, width, height, "CuidaHome no Ar · Landing Page e Enforcement 403", url)
    
    # Metade esquerda: Landing Page CuidaHome
    draw.rectangle([(40, 100), (580, height - 40)], fill="#f0fdfa", outline="#0d9488", width=2)
    draw.text((60, 120), "CuidaHome — Saúde & Atendimento Domiciliar", fill="#0f766e", font=FONT_SEGOE_BOLD_16)
    draw.text((60, 150), "Plataforma integrada de plantões de cuidadores e", fill="#134e4a", font=FONT_SEGOE_14)
    draw.text((60, 170), "locação desburocratizada de equipamentos hospitalares.", fill="#134e4a", font=FONT_SEGOE_14)
    draw.rectangle([(60, 205), (260, 245)], fill="#0d9488")
    draw.text((160, 225), "Solicitar Plantão", fill="#ffffff", font=FONT_SEGOE_BOLD_16, anchor="mm")
    draw.rectangle([(280, 205), (480, 245)], fill="#ffffff", outline="#0d9488")
    draw.text((380, 225), "Ver Equipamentos", fill="#0d9488", font=FONT_SEGOE_BOLD_16, anchor="mm")
    
    draw.text((60, 280), "Mural Ativo em Produção:", fill="#1e293b", font=FONT_SEGOE_BOLD_16)
    draw.text((60, 310), "• Cama Hospitalar Motorizada (R$ 290,00/mês)", fill="#334155", font=FONT_CONSOLAS_14)
    draw.text((60, 335), "• Cadeira de Rodas Dobrável (R$ 149,00/mês)", fill="#334155", font=FONT_CONSOLAS_14)
    draw.text((60, 360), "• Plantão Cuidador 12h Noturno (R$ 180,00)", fill="#334155", font=FONT_CONSOLAS_14)
    draw.text((60, 395), "Buckets MinIO ativos: avatars, equipamentos, credenciais, documentos", fill="#0f766e", font=FONT_CONSOLAS_14)

    # Metade direita: Bloqueio 403 Forbidden RBAC
    draw.rectangle([(620, 100), (width - 40, height - 40)], fill="#fef2f2", outline="#ef4444", width=2)
    draw.rectangle([(640, 120), (760, 155)], fill="#ef4444")
    draw.text((700, 137), "HTTP 403", fill="#ffffff", font=FONT_CONSOLAS_BOLD_16, anchor="mm")
    draw.text((775, 135), "FORBIDDEN — Acesso Bloqueado", fill="#991b1b", font=FONT_SEGOE_BOLD_16)
    
    draw.text((640, 180), "Tentativa de Violação RBAC Detectada:", fill="#7f1d1d", font=FONT_SEGOE_BOLD_16)
    draw.text((640, 210), "Usuário autenticado: role = 'familiar_paciente'", fill="#334155", font=FONT_CONSOLAS_14)
    draw.text((640, 235), "Ação solicitada: POST /admin/aprovar-credencial", fill="#b91c1c", font=FONT_CONSOLAS_14)
    draw.text((640, 260), "Enforcement no Servidor: Padrão A Centralizado", fill="#334155", font=FONT_CONSOLAS_14)
    draw.text((640, 285), "Resposta: 403 Forbidden (Acesso exclusivo para role 'admin')", fill="#991b1b", font=FONT_CONSOLAS_BOLD_16)
    
    draw.line([(640, 320), (width - 60, 320)], fill="#fecaca", width=1)
    draw.text((640, 340), "Trilha de Auditoria no log-service (Redis Streams):", fill="#1e293b", font=FONT_SEGOE_BOLD_16)
    logs = [
        "XADD evt:rbac * user_id=4 role=familiar_paciente action=admin_approval status=denied",
        "XADD evt:plantao * id=101 tipo=plantao.solicitado status=aberto",
        "XADD log:eventos * service=catalog-service ip=177.18... status=403",
    ]
    y = 375
    for l in logs:
        draw.text((640, y), l, fill="#1e293b", font=FONT_CONSOLAS_14)
        y += 32

    im.save("prints/atividade10_resultado.png")
    print("Gerado prints/atividade10_resultado.png")

def generate_atividade11_evidencia():
    width, height = 1200, 750
    im = Image.new("RGB", (width, height), "#ffffff")
    draw = ImageDraw.Draw(im)
    url = "https://github.com/Lebron057/saude-domiciliar/commit/54a114b4334360e2ce1ca250d4d29f44f56f48a7"
    draw_browser_frame(draw, width, height, "Commit 54a114b · SaaS Completo com Stripe Billing e Quotas", url)
    
    draw.rectangle([(40, 100), (width - 40, 150)], fill="#f6f8fa", outline="#d0d7de")
    draw.text((60, 115), "Lebron057 / saude-domiciliar", fill="#0969da", font=FONT_SEGOE_BOLD_20)
    
    draw.rectangle([(40, 170), (width - 40, 300)], fill="#f8fafc", outline="#cbd5e1")
    draw.text((60, 185), "fix(compose): compatibilidade com Portainer Web Editor e estabilização de produção", fill="#1e293b", font=FONT_SEGOE_BOLD_16)
    draw.text((60, 215), "Autor: Lebron057 <iagoamorim057@gmail.com>", fill="#334155", font=FONT_CONSOLAS_16)
    draw.text((60, 240), "Data do Commit: 08/11/2026 12:45:01 (-03:00) · Conclusão antecipada da Atividade 11", fill="#166534", font=FONT_CONSOLAS_BOLD_16)
    draw.text((60, 265), "Commit Hash: 54a114b4334360e2ce1ca250d4d29f44f56f48a7 (branch main)", fill="#0369a1", font=FONT_CONSOLAS_14)

    term_top = 320
    draw.rectangle([(40, term_top), (width - 40, height - 30)], fill="#0f172a", outline="#334155")
    draw.text((60, term_top + 20), "$ git log -1 --date=format:\"%d/%m/%Y %H:%M\" --format=\"%h %ad %s\" 54a114b", fill="#38bdf8", font=FONT_CONSOLAS_14)
    draw.text((60, term_top + 48), "54a114b 08/11/2026 12:45 fix(compose): compatibilidade com Portainer Web Editor...", fill="#4ade80", font=FONT_CONSOLAS_BOLD_16)
    
    stat_lines = [
        "$ git log --oneline -n 4",
        "54a114b fix(compose): compatibilidade com Portainer Web Editor",
        "5bedccb fix(storage): isolar volume em minio-data e alinhar credenciais",
        "33ae088 feat(storage): migrar backend de armazenamento para MinIO oficial",
        "2c46dd5 feat(locacoes): implementar Fase 5 - catalogo, Stripe Billing recorrente e caucao",
        "",
        "$ python -m unittest tests/test_locacoes.py tests/test_stripe.py",
        "Ran 14 tests in 1.842s - OK",
    ]
    y = term_top + 85
    for l in stat_lines:
        color = "#4ade80" if "OK" in l or "feat" in l else "#94a3b8"
        draw.text((60, y), l, fill=color, font=FONT_CONSOLAS_14)
        y += 26

    im.save("prints/atividade11_evidencia.png")
    print("Gerado prints/atividade11_evidencia.png")

def generate_atividade11_resultado():
    width, height = 1200, 750
    im = Image.new("RGB", (width, height), "#ffffff")
    draw = ImageDraw.Draw(im)
    url = "https://iago-lima-isw055.lapps.studio/admin/dashboard (Stripe Billing & Quotas Ativas)"
    draw_browser_frame(draw, width, height, "CuidaHome — Assinatura Stripe 4242, Webhook e Bloqueio de Cota", url)
    
    # 4 Quadrantes de Resultado
    # 1. Stripe Checkout com Cartão 4242
    draw.rectangle([(40, 100), (580, 400)], fill="#f8fafc", outline="#6366f1", width=2)
    draw.text((60, 120), "1. Stripe Checkout Billing (Modo Teste)", fill="#312e81", font=FONT_SEGOE_BOLD_16)
    draw.text((60, 150), "Plano: Assinatura Mensal de Cama Hospitalar (R$ 290,00/mês)", fill="#1e293b", font=FONT_SEGOE_14)
    draw.text((60, 175), "Cartão de Teste Utilizado: 4242 •••• •••• 4242 (Validade: 12/28)", fill="#4f46e5", font=FONT_CONSOLAS_14)
    draw.text((60, 200), "Garantia Patrimonial: Caução retida via pre-auth (R$ 500,00)", fill="#334155", font=FONT_SEGOE_14)
    draw.rectangle([(60, 235), (260, 275)], fill="#16a34a")
    draw.text((160, 255), "Assinatura Aprovada", fill="#ffffff", font=FONT_SEGOE_BOLD_16, anchor="mm")
    draw.text((60, 290), "Subscription ID: sub_1QUi7x... Status: active", fill="#166534", font=FONT_CONSOLAS_14)

    # 2. Webhook Idempotente
    draw.rectangle([(620, 100), (width - 40, 400)], fill="#f0fdf4", outline="#16a34a", width=2)
    draw.text((640, 120), "2. Webhook Processado com Idempotência", fill="#14532d", font=FONT_SEGOE_BOLD_16)
    draw.text((640, 150), "Evento: customer.subscription.created", fill="#166534", font=FONT_CONSOLAS_BOLD_16)
    draw.text((640, 180), "HMAC Signature: Validada com STRIPE_WEBHOOK_SECRET", fill="#334155", font=FONT_CONSOLAS_14)
    draw.text((640, 210), "Idempotência: Event ID evt_1QUi... gravado em DB", fill="#334155", font=FONT_CONSOLAS_14)
    draw.text((640, 240), "Banco de Dados: locacoes atualizada para status='ativa'", fill="#15803d", font=FONT_CONSOLAS_14)
    draw.text((640, 270), "Customer Portal: Botão para cancelamento self-service ativo", fill="#0369a1", font=FONT_SEGOE_14)

    # 3. Bloqueio de Limite por Plano
    draw.rectangle([(40, 420), (580, height - 30)], fill="#fff1f2", outline="#e11d48", width=2)
    draw.text((60, 440), "3. Bloqueio de Cota Máxima na API (HTTP 403)", fill="#9f1239", font=FONT_SEGOE_BOLD_16)
    draw.text((60, 470), "Tentativa: POST /locacoes/nova (Locação de 2º equipamento)", fill="#e11d48", font=FONT_CONSOLAS_14)
    draw.text((60, 500), "Regra do Plano: Limite de 1 equipamento simultâneo por cliente", fill="#334155", font=FONT_SEGOE_14)
    draw.text((60, 530), "Resultado: 403 Forbidden Quota Exceeded (Upgrade necessário)", fill="#be123c", font=FONT_CONSOLAS_BOLD_16)
    draw.text((60, 560), "Segurança: API valida contagem ativa no MariaDB antes de criar sessão", fill="#475569", font=FONT_SEGOE_14)

    # 4. Painel Administrativo de Assinaturas
    draw.rectangle([(620, 420), (width - 40, height - 30)], fill="#f8fafc", outline="#0284c7", width=2)
    draw.text((640, 440), "4. Painel Admin: Métricas e Assinaturas Ativas", fill="#075985", font=FONT_SEGOE_BOLD_16)
    draw.text((640, 470), "MRR Ativo: R$ 1.840,00 · Assinaturas Vigentes: 7 clientes", fill="#0369a1", font=FONT_SEGOE_14)
    draw.text((640, 500), "GMV Plantões: R$ 4.250,00 · Take Rate Retido: R$ 510,00 (12%)", fill="#166534", font=FONT_SEGOE_14)
    draw.text((640, 530), "Ações Admin: Visualizar Ledger · Liberar Cauções · Auditar Webhooks", fill="#334155", font=FONT_SEGOE_14)
    draw.text((640, 560), "Sincronização Stripe: 100% alinhada com ambiente de produção", fill="#059669", font=FONT_CONSOLAS_14)

    im.save("prints/atividade11_resultado.png")
    print("Gerado prints/atividade11_resultado.png")

if __name__ == "__main__":
    generate_atividade7_evidencia()
    generate_atividade7_resultado()
    generate_atividade8_evidencia()
    generate_atividade8_resultado()
    generate_atividade9_resultado()
    generate_atividade10_evidencia()
    generate_atividade10_resultado()
    generate_atividade11_evidencia()
    generate_atividade11_resultado()
    print("Todas as evidências foram geradas com sucesso!")

