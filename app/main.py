"""
CuidaHome — Saúde & Atendimento Domiciliar (Catalog Service / Gateway)
Ponto de entrada público da aplicação.
Responsabilidades:
- Interface do usuário (Jinja2 SSR) e arquivos estáticos.
- Landing page, catálogo de equipamentos e mural de plantões.
- Delegação de autenticação, papéis e recuperação de senha ao auth-service privado.
- Disparo de eventos de auditoria para o log-service.
- Rota de consulta de logs para administradores (/admin/logs).
- Perfil de usuário com upload de foto via MinIO S3 (Garage).
- Integração financeira com Stripe (Checkout, Billing e Webhooks).
"""

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, Request, Form, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database import init_db, get_connection
from app.auth import (
    login_user,
    register_user,
    get_current_user,
    request_password_reset,
    validate_reset_token,
    reset_password,
)
from app.minio_client import ensure_bucket, upload_avatar, delete_avatar, stream_avatar, MINIO_BUCKET
from minio.error import S3Error
import stripe
from app.stripe_service import (
    create_premium_checkout_session,
    verify_and_construct_webhook_event,
    is_stripe_configured,
)

# ── Configuração do MinIO ────────────────────────────────
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"
# Tamanho máximo de upload: 3 MB
MAX_UPLOAD_BYTES = 3 * 1024 * 1024
# MIME types permitidos para foto de perfil
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


# ── Configuração do Log Service ─────────────────────────
LOG_SERVICE_URL = os.getenv("LOG_SERVICE_URL", "http://log-service:8002").rstrip("/")


# ── Lifespan ────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: garante que as tabelas existam e o bucket MinIO esteja pronto
    try:
        init_db()
    except Exception as e:
        print(f"[CatalogService] Aviso ao inicializar banco: {e}")
    try:
        ensure_bucket()
    except Exception as e:
        print(f"[CatalogService] Aviso ao inicializar MinIO: {e}")
    yield


app = FastAPI(title="CuidaHome — Saúde & Atendimento Domiciliar", lifespan=lifespan)

# Montar arquivos estáticos e templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


# ── Helpers ─────────────────────────────────────────────
async def _get_user_or_none(request: Request) -> dict | None:
    """Tenta extrair o usuário do cookie e validar no auth-service."""
    try:
        return await get_current_user(request)
    except HTTPException:
        return None


async def _emit_log(
    usuario_id: int,
    acao: str,
    detalhe: str = "",
    ip_origem: str = "",
):
    """
    Dispara um evento de auditoria para o log-service via HTTP.
    Falhas são tratadas silenciosamente (try/except) para não
    derrubar a ação principal do usuário — log é 'best effort'.
    """
    try:
        payload = {
            "usuario_id": usuario_id,
            "acao": acao,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "detalhe": detalhe,
            "ip_origem": ip_origem,
        }
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(f"{LOG_SERVICE_URL}/logs", json=payload)
    except Exception as e:
        print(f"[CatalogService] Falha ao enviar log (best-effort): {e}")


def _get_client_ip(request: Request) -> str:
    """Extrai o IP de origem da requisição."""
    if request.client:
        return request.client.host
    return ""


def _require_admin(user: dict):
    """
    Dependency reutilizável de RBAC: exige role == 'admin'.
    Levanta HTTPException(403) caso contrário.
    """
    if user.get("role", "user") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Acesso negado: somente administradores.",
        )


# ══════════════════════════════════════════════════════════
#  ROTAS PÚBLICAS & AUTENTICAÇÃO (Delegadas ao auth-service)
# ══════════════════════════════════════════════════════════

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "catalog-service"}


@app.get("/", response_class=HTMLResponse)
async def root(request: Request, message: str = None, error: str = None):
    user = await _get_user_or_none(request)
    return templates.TemplateResponse("landing.html", {
        "request": request,
        "user": user,
        "active_page": "home",
        "message": message,
        "error": error,
    })


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, success: str = None, error: str = None):
    user = await _get_user_or_none(request)
    if user:
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("login.html", {
        "request": request,
        "user": None,
        "error": error,
        "success": success,
    })


@app.post("/login", response_class=HTMLResponse)
async def login_submit(request: Request, email: str = Form(...), senha: str = Form(...)):
    result = await login_user(email=email, senha=senha)

    if not result.get("success"):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "user": None,
            "error": result.get("error", "E-mail ou senha incorretos."),
        })

    token_data = result["data"]
    token = token_data["access_token"]

    # ── Evento de auditoria: login bem-sucedido ──
    user_data = token_data.get("user", {})
    await _emit_log(
        usuario_id=user_data.get("id", 0),
        acao="login",
        detalhe=f"email={email}",
        ip_origem=_get_client_ip(request),
    )

    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=86400,  # 24 horas
    )
    return response


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, error: str = None):
    user = await _get_user_or_none(request)
    if user:
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("register.html", {
        "request": request,
        "user": None,
        "error": error,
    })


@app.post("/register", response_class=HTMLResponse)
async def register_submit(
    request: Request,
    nome: str = Form(...),
    email: str = Form(...),
    senha: str = Form(...),
):
    if len(senha) < 6:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "user": None,
            "error": "A senha deve ter no mínimo 6 caracteres.",
        })

    result = await register_user(nome=nome, email=email, senha=senha, role="user")

    if not result.get("success"):
        return templates.TemplateResponse("register.html", {
            "request": request,
            "user": None,
            "error": result.get("error", "Erro ao cadastrar usuário."),
        })

    return RedirectResponse(
        url="/login?success=Conta+criada+com+sucesso!+Faça+login.",
        status_code=302,
    )


@app.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request, error: str = None, success: str = None):
    user = await _get_user_or_none(request)
    if user:
        return RedirectResponse(url="/catalog", status_code=302)
    return templates.TemplateResponse("forgot-password.html", {
        "request": request,
        "user": None,
        "error": error,
        "success": success,
    })


@app.post("/forgot-password", response_class=HTMLResponse)
async def forgot_password_submit(request: Request, email: str = Form(...)):
    # Montar URL pública base para inclusão no e-mail
    base_url = str(request.base_url).rstrip("/")
    result = await request_password_reset(email=email, base_url=base_url)

    if not result.get("success"):
        return templates.TemplateResponse("forgot-password.html", {
            "request": request,
            "user": None,
            "error": result.get("error", "Erro ao processar recuperação de senha."),
        })

    return templates.TemplateResponse("forgot-password.html", {
        "request": request,
        "user": None,
        "success": "Se o e-mail estiver cadastrado, as instruções e o link de recuperação foram enviados via Mailtrap.",
    })


@app.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(request: Request, token: str = ""):
    if not token:
        return templates.TemplateResponse("reset-password.html", {
            "request": request,
            "user": None,
            "valid_token": False,
            "error": "Token de recuperação não fornecido.",
        })

    # Validação do token junto ao auth-service
    validation = await validate_reset_token(token)

    if not validation.get("valid"):
        return templates.TemplateResponse("reset-password.html", {
            "request": request,
            "user": None,
            "valid_token": False,
            "error": validation.get("error", "Token inválido ou expirado."),
        })

    user_info = validation.get("data", {})
    return templates.TemplateResponse("reset-password.html", {
        "request": request,
        "user": None,
        "valid_token": True,
        "token": token,
        "email": user_info.get("email", ""),
        "error": None,
    })


@app.post("/reset-password", response_class=HTMLResponse)
async def reset_password_submit(
    request: Request,
    token: str = Form(...),
    nova_senha: str = Form(...),
    confirmar_senha: str = Form(...),
):
    if nova_senha != confirmar_senha:
        return templates.TemplateResponse("reset-password.html", {
            "request": request,
            "user": None,
            "valid_token": True,
            "token": token,
            "error": "As senhas não coincidem.",
        })

    if len(nova_senha) < 6:
        return templates.TemplateResponse("reset-password.html", {
            "request": request,
            "user": None,
            "valid_token": True,
            "token": token,
            "error": "A senha deve ter no mínimo 6 caracteres.",
        })

    result = await reset_password(token=token, nova_senha=nova_senha)

    if not result.get("success"):
        return templates.TemplateResponse("reset-password.html", {
            "request": request,
            "user": None,
            "valid_token": True,
            "token": token,
            "error": result.get("error", "Erro ao redefinir senha."),
        })

    return RedirectResponse(
        url="/login?success=Senha+redefinida+com+sucesso!+Faça+login+com+sua+nova+senha.",
        status_code=302,
    )


@app.get("/logout")
async def logout(request: Request):
    # ── Evento de auditoria: logout ──
    user = await _get_user_or_none(request)
    if user:
        await _emit_log(
            usuario_id=user["id"],
            acao="logout",
            detalhe=f"email={user.get('email', '')}",
            ip_origem=_get_client_ip(request),
        )
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("access_token")
    return response


# ══════════════════════════════════════════════════════════
#  ASSINATURA PREMIUM & WEBHOOK STRIPE (Atividade 7)
# ══════════════════════════════════════════════════════════

@app.get("/checkout/subscribe")
@app.post("/checkout/create-session")
async def checkout_subscribe(request: Request):
    """
    Inicia o fluxo de assinatura do Plano Premium.
    Cria uma Checkout Session no Stripe (em modo de teste) e redireciona
    o usuário autenticado diretamente para a página de pagamento hospedada pelo Stripe.
    Nenhum dado sensível de cartão trafega pela nossa aplicação.
    """
    user = await _get_user_or_none(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    if user.get("premium", False):
        return RedirectResponse(url="/catalog?message=Você+já+possui+o+Plano+Premium+ativo!", status_code=302)

    if not is_stripe_configured():
        return RedirectResponse(
            url="/catalog?error=O+sistema+de+pagamentos+Stripe+ainda+não+foi+configurado+pelo+administrador.",
            status_code=302,
        )

    try:
        base_url = str(request.base_url).rstrip("/")
        session = create_premium_checkout_session(
            usuario_id=user["id"],
            user_email=user["email"],
            user_nome=user["nome"],
            base_url=base_url,
        )

        await _emit_log(
            usuario_id=user["id"],
            acao="stripe.checkout_iniciado",
            detalhe=f"session_id={session.id}",
            ip_origem=_get_client_ip(request),
        )

        # Redirecionamento 303 (See Other) para a página hospedada pelo Stripe
        return RedirectResponse(url=session.url, status_code=303)
    except Exception as e:
        print(f"[Stripe] Erro ao criar Checkout Session: {e}")
        return RedirectResponse(
            url=f"/catalog?error=Erro+ao+iniciar+pagamento+no+Stripe:+{e}",
            status_code=302,
        )


@app.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """
    Endpoint de Webhook público chamado de forma assíncrona pelo Stripe.
    Validação Criptográfica Obrigatória: Verifica a assinatura no cabeçalho Stripe-Signature
    usando o STRIPE_WEBHOOK_SECRET antes de processar qualquer evento.
    Ao confirmar checkout.session.completed, atualiza MariaDB: premium = TRUE.
    """
    sig_header = request.headers.get("stripe-signature")
    if not sig_header:
        raise HTTPException(status_code=400, detail="Cabeçalho Stripe-Signature ausente.")

    payload = await request.body()

    try:
        event = verify_and_construct_webhook_event(payload, sig_header)
    except ValueError as e:
        print(f"[Webhook] Erro de configuração: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except stripe.SignatureVerificationError as e:
        print(f"[Webhook] Assinatura inválida rejeitada: {e}")
        raise HTTPException(status_code=400, detail="Assinatura criptográfica do Stripe inválida.")

    event_type = event.get("type", "")

    # Evento 1: Sessão de checkout concluída com sucesso
    if event_type == "checkout.session.completed":
        session = event["data"]["object"]
        usuario_id_str = session.get("client_reference_id") or (session.get("metadata") or {}).get("usuario_id")

        if usuario_id_str:
            usuario_id = int(usuario_id_str)
            customer_id = session.get("customer")
            subscription_id = session.get("subscription")

            conn = get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """UPDATE usuarios
                       SET premium = TRUE, stripe_customer_id = %s, stripe_subscription_id = %s
                       WHERE id = %s""",
                    (customer_id, subscription_id, usuario_id),
                )
                conn.commit()
            finally:
                cursor.close()
                conn.close()

            await _emit_log(
                usuario_id=usuario_id,
                acao="stripe.assinatura_ativada",
                detalhe=f"session_id={session.get('id')}, customer={customer_id}",
                ip_origem=_get_client_ip(request),
            )

    # Evento 2: Assinatura cancelada ou expirada
    elif event_type in ("customer.subscription.deleted", "customer.subscription.paused"):
        subscription = event["data"]["object"]
        subscription_id = subscription.get("id")
        if subscription_id:
            conn = get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "UPDATE usuarios SET premium = FALSE WHERE stripe_subscription_id = %s",
                    (subscription_id,),
                )
                conn.commit()
            finally:
                cursor.close()
                conn.close()

    return {"status": "success", "event_type": event_type}


# ══════════════════════════════════════════════════════════
#  ROTAS DE SAÚDE, EQUIPAMENTOS E PLANTÕES
# ══════════════════════════════════════════════════════════

@app.get("/catalog", response_class=HTMLResponse)
async def catalog_redirect():
    """Redirecionamento 301 do catálogo legado para a nova página inicial."""
    return RedirectResponse(url="/", status_code=301)


@app.get("/equipamentos", response_class=HTMLResponse)
async def equipamentos_page(request: Request):
    """Catálogo de equipamentos ortopédicos para locação."""
    user = await _get_user_or_none(request)
    return templates.TemplateResponse("landing.html", {
        "request": request,
        "user": user,
        "active_page": "equipamentos",
        "message": "Catálogo de equipamentos ortopédicos e hospitalares disponível para locação.",
        "error": None,
    })


@app.get("/profissionais", response_class=HTMLResponse)
async def profissionais_page(request: Request):
    """Mural de cuidadores e profissionais de enfermagem."""
    user = await _get_user_or_none(request)
    return templates.TemplateResponse("landing.html", {
        "request": request,
        "user": user,
        "active_page": "profissionais",
        "message": "Mural de plantões e profissionais de saúde certificados.",
        "error": None,
    })


@app.get("/painel/familia", response_class=HTMLResponse)
async def painel_familia_page(request: Request):
    """Área privativa para acompanhamento dos plantões e locações da família."""
    user = await _get_user_or_none(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("landing.html", {
        "request": request,
        "user": user,
        "active_page": "home",
        "message": f"Bem-vindo ao Painel da Família, {user.get('nome')}!",
        "error": None,
    })


@app.get("/favorites", response_class=HTMLResponse)
async def favorites_redirect():
    """Redirecionamento de favoritos legados."""
    return RedirectResponse(url="/", status_code=301)


# ══════════════════════════════════════════════════════════
#  ROTA DE ADMINISTRAÇÃO — CONSULTA DE LOGS (Atividade 5)
# ══════════════════════════════════════════════════════════

@app.get("/admin/logs", response_class=HTMLResponse)
async def admin_logs_page(request: Request, limit: int = 50, message: str = None):
    """
    Página de consulta de logs de auditoria — apenas admin.
    O catalog-service valida RBAC localmente e repassa a chamada
    para o log-service interno via httpx.
    """
    user = await _get_user_or_none(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    # ── Enforcement de RBAC ──
    if user.get("role", "user") != "admin":
        # Evento de auditoria: tentativa de acesso negado
        await _emit_log(
            usuario_id=user["id"],
            acao="acesso_negado_403",
            detalhe="tentativa de acessar /admin/logs sem permissão",
            ip_origem=_get_client_ip(request),
        )
        raise HTTPException(
            status_code=403,
            detail="Acesso negado: somente administradores.",
        )

    # ── Repassar chamada ao log-service interno ──
    logs = []
    error = None
    try:
        token = request.cookies.get("access_token", "")
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{LOG_SERVICE_URL}/logs",
                params={"limit": limit},
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code == 200:
                data = resp.json()
                logs = data.get("logs", [])
            else:
                error = f"Erro ao consultar log-service: HTTP {resp.status_code}"
    except Exception as e:
        error = f"Log-service indisponível: {e}"

    return templates.TemplateResponse("admin_logs.html", {
        "request": request,
        "user": user,
        "active_page": "admin_logs",
        "logs": logs,
        "limit": limit,
        "message": message,
        "error": error,
    })


# ══════════════════════════════════════════════════════════
#  ROTAS DE PERFIL DE USUÁRIO — MinIO (Atividade 6)
# ══════════════════════════════════════════════════════════

@app.get("/profile/{profile_user_id}", response_class=HTMLResponse)
async def profile_page(request: Request, profile_user_id: int, message: str = None, error: str = None):
    """
    Página de perfil pública: exibe foto (do MinIO), bio e filmes favoritados.
    O botão de edição só é renderizado quando o usuário logado é o dono do perfil.
    """
    user = await _get_user_or_none(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    # Buscar dados do usuário de perfil no banco
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id, nome, email, role, bio, avatar_key, premium FROM usuarios WHERE id = %s",
            (profile_user_id,),
        )
        profile_user = cursor.fetchone()
        if not profile_user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado.")

        # Lista de favoritos (polimórfica)
        favorites = []
    finally:
        cursor.close()
        conn.close()

    # Montar URL do avatar via proxy interno /storage/avatars/<filename>
    avatar_url = None
    if profile_user.get("avatar_key"):
        # Extrai apenas o nome do arquivo da chave (ex: "avatars/42-xxx.jpg" → "42-xxx.jpg")
        filename = profile_user["avatar_key"].split("/", 1)[-1]
        avatar_url = f"/storage/avatars/{filename}"

    is_own_profile = (user["id"] == profile_user_id)

    return templates.TemplateResponse("profile.html", {
        "request": request,
        "user": user,
        "active_page": "profile",
        "profile_user": profile_user,
        "avatar_url": avatar_url,
        "favorites": favorites,
        "is_own_profile": is_own_profile,
        "stripe_configured": is_stripe_configured(),
        "message": message,
        "error": error,
    })


@app.post("/profile/{profile_user_id}/upload")
async def profile_upload(
    request: Request,
    profile_user_id: int,
    bio: str = Form(""),
    foto: UploadFile = File(None),
):
    """
    Atualiza bio e/ou foto de perfil do usuário.
    Segurança:
      - O usuário SÓ pode editar o próprio perfil.
      - O user_id é extraído do JWT/sessão. O :id da URL é apenas para roteamento.
      - Validação de MIME type e tamanho no backend (nunca confiar apenas no frontend).
    """
    user = await _get_user_or_none(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    # ── Isolamento rígido: NUNCA confiar no ID da URL para autorizar edição ──
    if user["id"] != profile_user_id:
        await _emit_log(
            usuario_id=user["id"],
            acao="audit.security.access_denied",
            detalhe=f"tentativa de editar perfil do usuario_id={profile_user_id} (403)",
            ip_origem=_get_client_ip(request),
        )
        raise HTTPException(
            status_code=403,
            detail="Acesso negado: você só pode editar o seu próprio perfil.",
        )

    new_avatar_key = None

    # ── Processar upload de imagem (se enviado) ──
    if foto and foto.filename:
        # Garante que o bucket exista (lazy init — caso o Garage não estivesse
        # pronto quando o catalog-service iniciou)
        try:
            ensure_bucket()
        except Exception as _bucket_err:
            return RedirectResponse(
                url=f"/profile/{profile_user_id}?error=Storage+indisponível.+Tente+novamente+em+instantes.",
                status_code=302,
            )

        # Validação de MIME type no backend
        if foto.content_type not in ALLOWED_MIME_TYPES:
            return RedirectResponse(
                url=f"/profile/{profile_user_id}?error=Tipo+de+arquivo+inválido.+Envie+uma+imagem+JPEG,+PNG,+WEBP+ou+GIF.",
                status_code=302,
            )

        file_bytes = await foto.read()

        # Validação de tamanho no backend (≤ 3 MB)
        if len(file_bytes) > MAX_UPLOAD_BYTES:
            return RedirectResponse(
                url=f"/profile/{profile_user_id}?error=Arquivo+muito+grande.+Limite+máximo:+3+MB.",
                status_code=302,
            )

        # Buscar avatar antigo para remover (evitar objetos órfãos no MinIO)
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT avatar_key FROM usuarios WHERE id = %s", (user["id"],))
            row = cursor.fetchone()
            old_key = row["avatar_key"] if row else None
        finally:
            cursor.close()
            conn.close()

        # Upload da nova imagem para o MinIO
        try:
            new_avatar_key = upload_avatar(
                user_id=user["id"],
                file_bytes=file_bytes,
                filename=foto.filename,
                content_type=foto.content_type,
            )
        except S3Error as e:
            return RedirectResponse(
                url=f"/profile/{profile_user_id}?error=Erro+ao+enviar+imagem+para+o+storage.",
                status_code=302,
            )

        # Remover avatar anterior do MinIO (best-effort)
        if old_key:
            delete_avatar(old_key)

    # ── Persistir bio e/ou nova chave do avatar no MariaDB ──
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if new_avatar_key:
            cursor.execute(
                "UPDATE usuarios SET bio = %s, avatar_key = %s WHERE id = %s",
                (bio.strip() or None, new_avatar_key, user["id"]),
            )
        else:
            # Só a bio foi enviada — não apaga o avatar existente
            cursor.execute(
                "UPDATE usuarios SET bio = %s WHERE id = %s",
                (bio.strip() or None, user["id"]),
            )
        conn.commit()
    finally:
        cursor.close()
        conn.close()

    # ── Evento de auditoria: atualização de perfil ──
    await _emit_log(
        usuario_id=user["id"],
        acao="perfil.atualizado",
        detalhe=f"bio_atualizada={'sim' if bio.strip() else 'nao'}, foto_atualizada={'sim' if new_avatar_key else 'nao'}",
        ip_origem=_get_client_ip(request),
    )

    return RedirectResponse(
        url=f"/profile/{profile_user_id}?message=Perfil+atualizado+com+sucesso!",
        status_code=302,
    )


@app.get("/storage/avatars/{filename}")
async def serve_avatar(filename: str):
    """
    Proxy interno para servir imagens armazenadas no MinIO.
    O MinIO não expõe porta pública no host; o catalog-service faz o proxy.
    Isso segue o mesmo padrão do proxy /grafana descrito no auxiliar.
    """
    key = f"avatars/{filename}"
    try:
        response = stream_avatar(key)
        content_type = response.headers.get("Content-Type", "image/jpeg")
        data = response.read()
        response.close()
        response.release_conn()
        return Response(content=data, media_type=content_type)
    except S3Error:
        raise HTTPException(status_code=404, detail="Imagem não encontrada.")
