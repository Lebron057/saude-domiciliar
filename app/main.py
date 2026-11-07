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
from app.deps import require_roles, require_verified_professional, require_owner_or_admin
from app.services.storage import (
    ensure_buckets,
    upload_file,
    delete_file,
    stream_file,
    validate_file_upload,
    generate_key,
    S3_BUCKET_AVATARS,
    S3_BUCKET_EQUIPAMENTOS,
    S3_BUCKET_CREDENCIAIS,
    S3_BUCKET_DOCUMENTOS,
    ALLOWED_IMAGE_MIMES,
    ALLOWED_DOCUMENT_MIMES,
    MAX_AVATAR_BYTES,
    MAX_EQUIPAMENTO_BYTES,
    MAX_DOCUMENT_BYTES,
    S3Error,
)
import stripe
from app.stripe_service import (
    create_premium_checkout_session,
    verify_and_construct_webhook_event,
    is_stripe_configured,
)

# ── Configurações de Armazenamento e Limites ─────────────
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "garage:9000")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"
MAX_UPLOAD_BYTES = MAX_AVATAR_BYTES
ALLOWED_MIME_TYPES = ALLOWED_IMAGE_MIMES


# ── Configuração do Log Service ─────────────────────────
LOG_SERVICE_URL = os.getenv("LOG_SERVICE_URL", "http://log-service:8002").rstrip("/")


# ── Lifespan ────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: garante que as tabelas existam e os buckets S3 estejam provisionados
    try:
        init_db()
    except Exception as e:
        print(f"[CatalogService] Aviso ao inicializar banco: {e}")
    try:
        ensure_buckets()
    except Exception as e:
        print(f"[CatalogService] Aviso ao inicializar storage S3: {e}")
    yield


app = FastAPI(title="CuidaHome — Saúde & Atendimento Domiciliar", lifespan=lifespan)

# Incluir roteadores especializados
from app.routers.plantoes import router as plantoes_router
from app.services.plantoes import confirmar_pagamento_plantao

app.include_router(plantoes_router)

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
    role: str = Form("familiar_paciente"),
):
    if len(senha) < 6:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "user": None,
            "error": "A senha deve ter no mínimo 6 caracteres.",
        })

    result = await register_user(nome=nome, email=email, senha=senha, role=role)

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

    event_id = event.get("id")
    event_type = event.get("type", "")

    # Idempotência no processamento de eventos do Stripe via tabela stripe_eventos
    if event_id:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT IGNORE INTO stripe_eventos (event_id, tipo) VALUES (%s, %s)",
                (event_id, event_type),
            )
            conn.commit()
            if cursor.rowcount == 0:
                # Evento já recebido e registrado anteriormente (idempotência estrita)
                return {"status": "duplicate_ignored", "event_id": event_id}
        finally:
            cursor.close()
            conn.close()

    # Evento 1: Sessão de checkout concluída com sucesso
    if event_type == "checkout.session.completed":
        session = event["data"]["object"]
        metadata = session.get("metadata") or {}
        tipo = metadata.get("tipo")

        # Roteamento 1A: Pagamento de Plantão Domiciliar (DoD 2)
        if tipo == "plantao" and metadata.get("plantao_id"):
            plantao_id = int(metadata["plantao_id"])
            session_id = session.get("id")
            payment_intent = session.get("payment_intent")

            confirmar_pagamento_plantao(
                plantao_id=plantao_id,
                stripe_session_id=session_id,
                stripe_payment_intent_id=payment_intent,
            )

            if event_id:
                conn = get_connection()
                cursor = conn.cursor()
                try:
                    cursor.execute(
                        "UPDATE stripe_eventos SET processado_em = NOW() WHERE event_id = %s",
                        (event_id,),
                    )
                    conn.commit()
                finally:
                    cursor.close()
                    conn.close()

            await _emit_log(
                usuario_id=int(session.get("client_reference_id") or 0),
                acao="plantao.confirmado",
                detalhe=f"plantao_id={plantao_id}, session_id={session_id}",
                ip_origem=_get_client_ip(request),
            )
            return {"status": "plantao_confirmed", "plantao_id": plantao_id}

        # Roteamento 1B: Assinatura / Locação de Equipamentos ou Legado
        usuario_id_str = session.get("client_reference_id") or metadata.get("usuario_id")

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
                if event_id:
                    cursor.execute(
                        "UPDATE stripe_eventos SET processado_em = NOW() WHERE event_id = %s",
                        (event_id,),
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
        try:
            ensure_buckets()
        except Exception as _bucket_err:
            return RedirectResponse(
                url=f"/profile/{profile_user_id}?error=Storage+indispon%C3%ADvel.+Tente+novamente+em+instantes.",
                status_code=302,
            )

        file_bytes = await foto.read()

        # Validação profunda: MIME type, tamanho (≤ 3 MB) e verificação de magic bytes
        is_valid, msg_or_mime, ext = validate_file_upload(
            file_bytes=file_bytes,
            filename=foto.filename,
            content_type=foto.content_type,
            allowed_mime_types=ALLOWED_IMAGE_MIMES,
            max_bytes=MAX_AVATAR_BYTES,
        )
        if not is_valid:
            import urllib.parse
            err_enc = urllib.parse.quote_plus(msg_or_mime)
            return RedirectResponse(
                url=f"/profile/{profile_user_id}?error={err_enc}",
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

        # Upload da nova imagem para o S3 (bucket avatars)
        new_key = generate_key("avatars", user["id"], ext)
        try:
            new_avatar_key = upload_file(
                bucket_name=S3_BUCKET_AVATARS,
                key=new_key,
                file_bytes=file_bytes,
                content_type=msg_or_mime,
            )
        except Exception as e:
            return RedirectResponse(
                url=f"/profile/{profile_user_id}?error=Erro+ao+enviar+imagem+para+o+storage.",
                status_code=302,
            )

        # Remover avatar anterior do MinIO (best-effort)
        if old_key:
            delete_file(S3_BUCKET_AVATARS, old_key)

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


# ══════════════════════════════════════════════════════════
#  ROTAS DE STORAGE S3 / GARAGE — PROXIES PÚBLICOS E PRIVADOS (Fase 3)
# ══════════════════════════════════════════════════════════

@app.get("/storage/avatars/{filename}")
async def serve_avatar(filename: str):
    """
    Proxy interno para servir imagens do bucket 'avatars'.
    Cache público com TTL de 24h e proteção nosniff.
    """
    key = f"avatars/{filename}" if not filename.startswith("avatars/") else filename
    try:
        response = stream_file(S3_BUCKET_AVATARS, key)
        content_type = response.headers.get("Content-Type", "image/jpeg")
        data = response.read()
        response.close()
        response.release_conn()
        return Response(
            content=data,
            media_type=content_type,
            headers={
                "Cache-Control": "public, max-age=86400",
                "X-Content-Type-Options": "nosniff",
            },
        )
    except Exception:
        raise HTTPException(status_code=404, detail="Imagem não encontrada.")


@app.get("/storage/equipamentos/{equipamento_id}/{filename}")
async def serve_equipamento_foto(equipamento_id: int, filename: str):
    """
    Proxy interno público para fotos do catálogo de equipamentos ortopédicos.
    """
    key = f"equipamentos/{equipamento_id}/{filename}"
    try:
        response = stream_file(S3_BUCKET_EQUIPAMENTOS, key)
        content_type = response.headers.get("Content-Type", "image/jpeg")
        data = response.read()
        response.close()
        response.release_conn()
        return Response(
            content=data,
            media_type=content_type,
            headers={
                "Cache-Control": "public, max-age=86400",
                "X-Content-Type-Options": "nosniff",
            },
        )
    except Exception:
        raise HTTPException(status_code=404, detail="Foto de equipamento não encontrada.")


@app.get("/documentos/credenciais/{credencial_id}")
async def get_documento_credencial(request: Request, credencial_id: int):
    """
    Proxy autenticado para credenciais de profissionais de saúde (COREN, diplomas).
    Controle estrito RBAC/IDOR:
      - Acessível APENAS pelo profissional dono da credencial ou por administradores.
      - Usuários do tipo familiar_paciente ou terceiros recebem HTTP 403 Forbidden.
    """
    user = await _get_user_or_none(request)
    if not user:
        raise HTTPException(status_code=401, detail="Autenticação obrigatória.")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id, usuario_id, tipo, object_key, mime, status FROM credenciais WHERE id = %s",
            (credencial_id,),
        )
        credencial = cursor.fetchone()
    finally:
        cursor.close()
        conn.close()

    if not credencial:
        raise HTTPException(status_code=404, detail="Credencial não encontrada.")

    # Enforcement de RBAC / IDOR
    is_admin = (user.get("role") == "admin")
    is_owner = (user.get("id") == credencial["usuario_id"])

    if not (is_admin or is_owner):
        await _emit_log(
            usuario_id=user["id"],
            acao="audit.security.access_denied",
            detalhe=f"tentativa de acessar credencial {credencial_id} do usuario_id={credencial['usuario_id']} (403)",
            ip_origem=_get_client_ip(request),
        )
        raise HTTPException(
            status_code=403,
            detail="Acesso negado: apenas o profissional titular ou administradores podem acessar esta credencial.",
        )

    # Obter stream do objeto no bucket privado de credenciais
    try:
        response = stream_file(S3_BUCKET_CREDENCIAIS, credencial["object_key"])
        data = response.read()
        response.close()
        response.release_conn()
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Arquivo de credencial não encontrado no storage: {e}")

    await _emit_log(
        usuario_id=user["id"],
        acao="documento.acessado",
        detalhe=f"credencial_id={credencial_id}, tipo={credencial['tipo']}, status={credencial['status']}",
        ip_origem=_get_client_ip(request),
    )

    mime = credencial.get("mime") or "application/pdf"
    ext = "pdf" if "pdf" in mime else "jpg"
    filename = f"credencial_{credencial['tipo']}_{credencial_id}.{ext}"

    return Response(
        content=data,
        media_type=mime,
        headers={
            "Content-Disposition": f"inline; filename=\"{filename}\"",
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-transform, no-store",
        },
    )


@app.get("/documentos/laudos/{documento_id}")
async def get_documento_laudo(request: Request, documento_id: int):
    """
    Proxy autenticado para laudos médicos e prescrições de pacientes (LGPD / Dados Sensíveis).
    Controle RBAC/ABAC:
      - Administrador tem acesso total para fins de auditoria/suporte.
      - Familiar responsável pelo paciente tem acesso.
      - Profissional de saúde tem acesso se e somente se possuir plantão confirmado/em andamento com o paciente.
      - Terceiros recebem HTTP 403 Forbidden.
    """
    user = await _get_user_or_none(request)
    if not user:
        raise HTTPException(status_code=401, detail="Autenticação obrigatória.")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT d.id, d.paciente_id, d.locacao_id, d.criado_por, d.tipo, d.object_key, d.mime,
                   p.familiar_id, p.nome AS paciente_nome
            FROM documentos d
            LEFT JOIN pacientes p ON d.paciente_id = p.id
            WHERE d.id = %s
            """,
            (documento_id,),
        )
        doc = cursor.fetchone()

        if not doc:
            raise HTTPException(status_code=404, detail="Documento médico não encontrado.")

        is_admin = (user.get("role") == "admin")
        is_familiar = (user.get("id") == doc.get("familiar_id") or user.get("id") == doc.get("criado_por"))
        is_assigned_pro = False

        if user.get("role") == "profissional_saude" and doc.get("paciente_id"):
            cursor.execute(
                """
                SELECT id FROM plantoes
                WHERE paciente_id = %s AND profissional_id = %s
                  AND status IN ('aceito', 'confirmado', 'em_andamento')
                LIMIT 1
                """,
                (doc["paciente_id"], user["id"]),
            )
            if cursor.fetchone():
                is_assigned_pro = True
    finally:
        cursor.close()
        conn.close()

    if not (is_admin or is_familiar or is_assigned_pro):
        await _emit_log(
            usuario_id=user["id"],
            acao="audit.security.access_denied",
            detalhe=f"tentativa de acessar laudo medico documento_id={documento_id} do paciente_id={doc.get('paciente_id')} (403)",
            ip_origem=_get_client_ip(request),
        )
        raise HTTPException(
            status_code=403,
            detail="Acesso negado: documento sigiloso restrito ao familiar e ao profissional designado para o plantão.",
        )

    try:
        response = stream_file(S3_BUCKET_DOCUMENTOS, doc["object_key"])
        data = response.read()
        response.close()
        response.release_conn()
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Arquivo não encontrado no storage: {e}")

    await _emit_log(
        usuario_id=user["id"],
        acao="documento.acessado",
        detalhe=f"documento_id={documento_id}, paciente_id={doc.get('paciente_id')}, tipo={doc.get('tipo')}",
        ip_origem=_get_client_ip(request),
    )

    mime = doc.get("mime") or "application/pdf"
    ext = "pdf" if "pdf" in mime else "jpg"
    filename = f"laudo_{doc.get('tipo')}_{documento_id}.{ext}"

    return Response(
        content=data,
        media_type=mime,
        headers={
            "Content-Disposition": f"attachment; filename=\"{filename}\"",
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-transform, no-store",
        },
    )


@app.get("/documentos/vistoria/{movimentacao_id}")
async def get_documento_vistoria(request: Request, movimentacao_id: int):
    """
    Proxy autenticado para fotos de vistoria e entrega de equipamentos ortopédicos.
    Acessível apenas pelo cliente locatário, fornecedor do equipamento ou administrador.
    """
    user = await _get_user_or_none(request)
    if not user:
        raise HTTPException(status_code=401, detail="Autenticação obrigatória.")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT m.id, m.locacao_id, m.responsavel_id, m.tipo, m.foto_vistoria_key,
                   l.cliente_id, eq.fornecedor_id
            FROM movimentacoes_locacao m
            JOIN locacoes l ON m.locacao_id = l.id
            JOIN equipamentos eq ON l.equipamento_id = eq.id
            WHERE m.id = %s
            """,
            (movimentacao_id,),
        )
        mov = cursor.fetchone()
    finally:
        cursor.close()
        conn.close()

    if not mov or not mov.get("foto_vistoria_key"):
        raise HTTPException(status_code=404, detail="Registro ou foto de vistoria não encontrado.")

    is_admin = (user.get("role") == "admin")
    is_client = (user.get("id") == mov.get("cliente_id"))
    is_supplier = (user.get("id") == mov.get("fornecedor_id"))

    if not (is_admin or is_client or is_supplier):
        await _emit_log(
            usuario_id=user["id"],
            acao="audit.security.access_denied",
            detalhe=f"tentativa de acessar vistoria movimentacao_id={movimentacao_id} sem permissão (403)",
            ip_origem=_get_client_ip(request),
        )
        raise HTTPException(
            status_code=403,
            detail="Acesso negado: vistoria restrita ao locatário, fornecedor e administração.",
        )

    try:
        response = stream_file(S3_BUCKET_DOCUMENTOS, mov["foto_vistoria_key"])
        data = response.read()
        response.close()
        response.release_conn()
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Arquivo não encontrado no storage: {e}")

    await _emit_log(
        usuario_id=user["id"],
        acao="documento.acessado",
        detalhe=f"vistoria_movimentacao_id={movimentacao_id}, locacao_id={mov.get('locacao_id')}",
        ip_origem=_get_client_ip(request),
    )

    return Response(
        content=data,
        media_type="image/jpeg",
        headers={
            "Content-Disposition": f"inline; filename=\"vistoria_{movimentacao_id}.jpg\"",
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-transform, no-store",
        },
    )


@app.post("/profissionais/credenciais/upload")
async def upload_credencial_profissional(
    request: Request,
    tipo: str = Form(...),
    documento: UploadFile = File(...),
):
    """
    Upload de credencial de saúde (COREN, diploma, certidão de antecedentes).
    Validação obrigatória de magic bytes: arquivos maliciosos (ex: executáveis com extensão .pdf)
    são sumariamente rejeitados com HTTP 400 Bad Request.
    """
    user = await _get_user_or_none(request)
    if not user:
        raise HTTPException(status_code=401, detail="Autenticação obrigatória.")

    if user.get("role") not in ("profissional_saude", "admin"):
        raise HTTPException(status_code=403, detail="Apenas profissionais de saúde podem enviar credenciais.")

    tipos_validos = {
        "coren", "diploma", "antecedentes", "documento_identidade",
        "comprovante_endereco", "certificado_curso", "cnpj_alvara",
    }
    if tipo not in tipos_validos:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de credencial inválido. Válidos: {', '.join(sorted(tipos_validos))}",
        )

    if not documento or not documento.filename:
        raise HTTPException(status_code=400, detail="Nenhum arquivo enviado.")

    file_bytes = await documento.read()

    # Validação profunda: extensão, tamanho e magic bytes
    is_valid, msg_or_mime, ext = validate_file_upload(
        file_bytes=file_bytes,
        filename=documento.filename,
        content_type=documento.content_type,
        allowed_mime_types=ALLOWED_DOCUMENT_MIMES,
        max_bytes=MAX_DOCUMENT_BYTES,
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail=msg_or_mime)

    key = generate_key(f"credenciais/{tipo}", user["id"], ext)

    try:
        upload_file(
            bucket_name=S3_BUCKET_CREDENCIAIS,
            key=key,
            file_bytes=file_bytes,
            content_type=msg_or_mime,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha ao salvar no storage: {e}")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            INSERT INTO credenciais (usuario_id, tipo, object_key, mime, tamanho_bytes, status)
            VALUES (%s, %s, %s, %s, %s, 'pendente')
            """,
            (user["id"], tipo, key, msg_or_mime, len(file_bytes)),
        )
        credencial_id = cursor.lastrowid

        # Atualiza status do perfil profissional para 'em_analise' caso estivesse 'pendente'
        cursor.execute(
            """
            UPDATE perfis_profissionais
            SET status_verificacao = 'em_analise'
            WHERE usuario_id = %s AND status_verificacao = 'pendente'
            """,
            (user["id"],),
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()

    await _emit_log(
        usuario_id=user["id"],
        acao="credencial.enviada",
        detalhe=f"credencial_id={credencial_id}, tipo={tipo}, bytes={len(file_bytes)}",
        ip_origem=_get_client_ip(request),
    )

    return {
        "success": True,
        "credencial_id": credencial_id,
        "tipo": tipo,
        "object_key": key,
        "status": "pendente",
        "message": "Credencial enviada com sucesso para análise.",
    }


@app.post("/pacientes/{paciente_id}/documentos/upload")
async def upload_documento_paciente(
    request: Request,
    paciente_id: int,
    tipo: str = Form("laudo_medico"),
    descricao: str = Form(""),
    documento: UploadFile = File(...),
):
    """
    Upload de laudo médico ou prescrição de paciente vinculado ao familiar responsável.
    """
    user = await _get_user_or_none(request)
    if not user:
        raise HTTPException(status_code=401, detail="Autenticação obrigatória.")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT familiar_id FROM pacientes WHERE id = %s", (paciente_id,))
        paciente = cursor.fetchone()
    finally:
        cursor.close()
        conn.close()

    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente não encontrado.")

    is_admin = (user.get("role") == "admin")
    is_owner = (user.get("id") == paciente["familiar_id"])
    if not (is_admin or is_owner):
        raise HTTPException(
            status_code=403,
            detail="Acesso negado: apenas o familiar responsável ou administradores podem anexar laudos.",
        )

    if not documento or not documento.filename:
        raise HTTPException(status_code=400, detail="Nenhum arquivo enviado.")

    file_bytes = await documento.read()

    is_valid, msg_or_mime, ext = validate_file_upload(
        file_bytes=file_bytes,
        filename=documento.filename,
        content_type=documento.content_type,
        allowed_mime_types=ALLOWED_DOCUMENT_MIMES,
        max_bytes=MAX_DOCUMENT_BYTES,
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail=msg_or_mime)

    key = generate_key(f"pacientes/{paciente_id}/documentos", user["id"], ext)

    try:
        upload_file(
            bucket_name=S3_BUCKET_DOCUMENTOS,
            key=key,
            file_bytes=file_bytes,
            content_type=msg_or_mime,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha ao salvar no storage: {e}")

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO documentos (paciente_id, criado_por, tipo, object_key, mime, tamanho_bytes, descricao)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (paciente_id, user["id"], tipo, key, msg_or_mime, len(file_bytes), descricao.strip() or None),
        )
        doc_id = cursor.lastrowid
        conn.commit()
    finally:
        cursor.close()
        conn.close()

    await _emit_log(
        usuario_id=user["id"],
        acao="documento.enviado",
        detalhe=f"documento_id={doc_id}, paciente_id={paciente_id}, tipo={tipo}",
        ip_origem=_get_client_ip(request),
    )

    return {
        "success": True,
        "documento_id": doc_id,
        "tipo": tipo,
        "object_key": key,
        "message": "Documento médico anexado com sucesso.",
    }
