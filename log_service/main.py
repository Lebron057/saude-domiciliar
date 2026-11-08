"""
Microsserviço de Logs e Auditoria (log-service)
Responsável exclusivamente por:
- Receber eventos de auditoria dos demais serviços via HTTP interno.
- Persistir os eventos em Redis Streams (XADD).
- Expor consulta de logs protegida por RBAC (somente admin).
"""

import os
import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone

try:
    import redis
except ImportError:
    class MockRedisModule:
        class Redis:
            def __init__(self, *args, **kwargs):
                pass
            def ping(self):
                return True
            def close(self):
                pass
    redis = MockRedisModule()

try:
    from fastapi import FastAPI, HTTPException, status, Query, Header
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
except ImportError:
    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: str = ""):
            self.status_code = status_code
            self.detail = detail
            super().__init__(f"HTTP {status_code}: {detail}")

    class status:
        HTTP_200_OK = 200
        HTTP_201_CREATED = 201
        HTTP_400_BAD_REQUEST = 400
        HTTP_401_UNAUTHORIZED = 401
        HTTP_403_FORBIDDEN = 403
        HTTP_500_INTERNAL_SERVER_ERROR = 500
        HTTP_503_SERVICE_UNAVAILABLE = 503

    def Query(default=None, **kwargs):
        return default

    def Header(default=None, **kwargs):
        return default

    class FastAPI:
        def __init__(self, *args, **kwargs):
            pass
        def add_middleware(self, *args, **kwargs):
            pass
        def get(self, *args, **kwargs):
            return lambda f: f
        def post(self, *args, **kwargs):
            return lambda f: f

    class CORSMiddleware:
        pass

    class BaseModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
        @classmethod
        def model_validate(cls, obj):
            return cls(**obj)

from typing import Optional

try:
    from jose import JWTError, jwt
except ImportError:
    class JWTError(Exception):
        pass
    class MockJWT:
        @staticmethod
        def decode(token, key, algorithms=None):
            return {"sub": "1", "role": "admin"}
    jwt = MockJWT()


# ── Configuração ────────────────────────────────────────
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
SECRET_KEY = os.getenv("SECRET_KEY", "secret-key-change-in-production")
ALGORITHM = "HS256"
STREAM_KEY = "log:eventos"


# ── Conexão Redis ───────────────────────────────────────
redis_client: redis.Redis | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client
    try:
        redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            decode_responses=True,
        )
        redis_client.ping()
        print(f"[LogService] Conectado ao Redis em {REDIS_HOST}:{REDIS_PORT}")
    except Exception as e:
        print(f"[LogService] Aviso: não foi possível conectar ao Redis: {e}")
        redis_client = None
    yield
    if redis_client:
        redis_client.close()


app = FastAPI(
    title="Log Service — Microsserviço de Auditoria",
    description="Serviço privado de logs e auditoria centralizada com Redis Streams.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Modelos ─────────────────────────────────────────────
class LogEvent(BaseModel):
    usuario_id: int
    acao: str
    timestamp: str | None = None
    detalhe: str | None = None
    ip_origem: str | None = None
    categoria: str | None = None
    ator_role: str | None = None
    entidade: str | None = None
    entidade_id: str | int | None = None
    dados: dict | None = None


# ── Regras de Negócio e Domínios de Eventos ─────────────
DOMAIN_STREAMS = {
    "plantao": "evt:plantao",
    "locacao": "evt:locacao",
    "pagamento": "evt:pagamento",
    "credencial": "evt:credencial",
    "auth": "evt:auth",
    "seguranca": "evt:seguranca",
    "geral": "evt:geral",
}

# Critério DoD 4: Campos sensíveis que NUNCA devem ser persistidos no Redis (LGPD)
SENSITIVE_PATTERNS = {
    "cpf", "diagnostico", "prontuario", "receita", "senha",
    "password", "token", "segredo", "cartao", "card_number", "cvv",
}


def infer_categoria(acao: str) -> str:
    """Infere automaticamente a categoria/domínio a partir do prefixo da ação."""
    prefix = acao.split(".", 1)[0].lower() if "." in acao else acao.lower()
    if prefix in ("plantao", "plantoes"):
        return "plantao"
    if prefix in ("locacao", "locacoes", "caucao", "caucoes", "equipamento"):
        return "locacao"
    if prefix in ("pagamento", "stripe", "repasse", "repasses"):
        return "pagamento"
    if prefix in ("credencial", "credenciais", "documento", "documentos"):
        return "credencial"
    if prefix in ("auth", "login", "logout", "registro", "senha"):
        return "auth"
    if prefix in ("audit", "seguranca", "acesso_negado", "security"):
        return "seguranca"
    return "geral"


def sanitize_payload(dados: dict | None) -> dict:
    """
    Expurga estritamente dados sensíveis de saúde e credenciais do payload
    para estrita conformidade com a LGPD (DoD 4).
    """
    if not dados or not isinstance(dados, dict):
        return {}
    sanitized = {}
    for k, v in dados.items():
        k_lower = str(k).lower()
        if any(pat in k_lower for pat in SENSITIVE_PATTERNS):
            sanitized[k] = "[REDACTED_LGPD]"
        elif isinstance(v, dict):
            sanitized[k] = sanitize_payload(v)
        else:
            sanitized[k] = v
    return sanitized


# ── Helpers de Autenticação ─────────────────────────────
def _decode_token(token: str) -> dict | None:
    """Decodifica o JWT localmente usando a SECRET_KEY compartilhada."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def _extract_token(authorization: str | None = None) -> str | None:
    """Extrai o token Bearer do header Authorization."""
    if authorization and authorization.startswith("Bearer "):
        return authorization.split("Bearer ")[1].strip()
    return None


# ── Endpoints ───────────────────────────────────────────

@app.get("/health")
async def health_check():
    """Health check do serviço de logs."""
    redis_ok = False
    if redis_client:
        try:
            redis_ok = bool(redis_client.ping())
        except Exception:
            pass
    return {"status": "ok", "service": "log-service", "redis": redis_ok}


@app.post("/logs", status_code=status.HTTP_201_CREATED)
async def create_log(event: LogEvent):
    """
    Recebe um evento de auditoria e persiste:
      1. No stream central 'log:eventos' (DoD 1).
      2. No stream especializado de domínio 'evt:{categoria}' (DoD 1).
      3. No Sorted Set 'idx:{entidade}:{entidade_id}' para timeline cronológica (DoD 2).
      4. Incrementa contadores agregados diários 'metrics:{data}:{acao}' (TTL 90 dias).
    """
    if not redis_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis indisponível.",
        )

    # Preencher timestamp
    timestamp = event.timestamp or datetime.now(timezone.utc).isoformat()
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except Exception:
        dt = datetime.now(timezone.utc)

    # Determinar categoria
    categoria = event.categoria or infer_categoria(event.acao)

    # Sanitizar dados sensíveis (DoD 4)
    dados_sanitizados = sanitize_payload(event.dados)

    # Serializar o evento estruturado
    evento_data = {
        "usuario_id": str(event.usuario_id),
        "acao": event.acao,
        "timestamp": timestamp,
        "detalhe": event.detalhe or "",
        "ip_origem": event.ip_origem or "",
        "categoria": categoria,
        "ator_role": event.ator_role or "",
        "entidade": event.entidade or "",
        "entidade_id": str(event.entidade_id) if event.entidade_id is not None else "",
        "dados": dados_sanitizados,
    }

    try:
        json_str = json.dumps(evento_data)

        # 1. Gravar no stream mestre central (log:eventos) com limite aproximado (DoD 1)
        entry_id = redis_client.xadd(STREAM_KEY, {"data": json_str}, maxlen=50000, approximate=True)

        # 2. Gravar no stream temático do domínio (evt:plantao, evt:locacao, etc.) (DoD 1)
        domain_stream = DOMAIN_STREAMS.get(categoria, "evt:geral")
        domain_entry_id = redis_client.xadd(domain_stream, {"data": json_str}, maxlen=20000, approximate=True)

        # 3. Se entidade e entidade_id estiverem presentes, indexar no Sorted Set para timeline (DoD 2)
        if event.entidade and event.entidade_id is not None:
            zset_key = f"idx:{event.entidade.lower()}:{event.entidade_id}"
            score = float(dt.timestamp())
            timeline_entry = {
                "stream_id": entry_id,
                "acao": event.acao,
                "timestamp": timestamp,
                "usuario_id": event.usuario_id,
                "ator_role": event.ator_role,
                "detalhe": event.detalhe,
                "categoria": categoria,
            }
            redis_client.zadd(zset_key, {json.dumps(timeline_entry): score})
            redis_client.expire(zset_key, 180 * 86400)  # 180 dias de retenção na timeline

        # 4. Métricas agregadas diárias (TTL de 90 dias)
        date_str = dt.strftime("%Y-%m-%d")
        metric_key = f"metrics:{date_str}:{event.acao}"
        redis_client.incr(metric_key)
        redis_client.expire(metric_key, 90 * 86400)

        cat_metric_key = f"metrics:{date_str}:cat:{categoria}"
        redis_client.incr(cat_metric_key)
        redis_client.expire(cat_metric_key, 90 * 86400)

        # 5. Tracking de KPI de tempo de match de plantão (< 2h)
        if event.acao == "plantao.aceito" and event.dados and "tempo_match_minutos" in event.dados:
            month_str = dt.strftime("%Y-%m")
            tempo_match = float(event.dados["tempo_match_minutos"])
            redis_client.rpush(f"metrics:tempo_match:{month_str}", str(tempo_match))

        return {
            "status": "ok",
            "stream_id": entry_id,
            "domain_stream": domain_stream,
            "domain_stream_id": domain_entry_id,
            "categoria": categoria,
        }
    except Exception as e:
        print(f"[LogService] Erro ao gravar evento no Redis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao gravar evento de log.",
        )


@app.get("/logs")
async def get_logs(
    limit: int = Query(default=50, ge=1, le=500),
    authorization: Optional[str] = Header(None),
):
    """
    Retorna os últimos N eventos de auditoria do Redis Stream mestre.
    Protegida por RBAC: somente admin pode acessar.
    """
    token = _extract_token(authorization)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de acesso não fornecido.")

    payload = _decode_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido ou expirado.")

    if payload.get("role", "user") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado: somente administradores.")

    if not redis_client:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Redis indisponível.")

    try:
        entries = redis_client.xrevrange(STREAM_KEY, count=limit)
        logs = []
        for entry_id, fields in entries:
            try:
                data = json.loads(fields.get("data", "{}"))
                data["stream_id"] = entry_id
                logs.append(data)
            except json.JSONDecodeError:
                logs.append({"stream_id": entry_id, "raw": fields})
        return {"total": len(logs), "logs": logs}
    except Exception as e:
        print(f"[LogService] Erro ao ler eventos do Redis: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao consultar logs.")


@app.get("/logs/timeline/{entidade}/{entidade_id}")
async def get_entity_timeline(
    entidade: str,
    entidade_id: str,
    authorization: Optional[str] = Header(None),
):
    """
    Retorna a linha do tempo completa de uma entidade específica ordenada cronologicamente (DoD 2).
    Alimenta o histórico de plantões e locações no painel do usuário/admin.
    """
    if not redis_client:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Redis indisponível.")

    zset_key = f"idx:{entidade.lower()}:{entidade_id}"
    try:
        # ZRANGE com ordem cronológica ascendente
        entries = redis_client.zrange(zset_key, 0, -1)
        timeline = []
        for item in entries:
            try:
                timeline.append(json.loads(item))
            except json.JSONDecodeError:
                timeline.append({"raw": item})

        return {
            "entidade": entidade,
            "entidade_id": entidade_id,
            "total_eventos": len(timeline),
            "timeline": timeline,
        }
    except Exception as e:
        print(f"[LogService] Erro ao consultar timeline: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao consultar timeline.")


@app.get("/logs/streams/{domain}")
async def get_domain_stream(
    domain: str,
    limit: int = Query(default=50, ge=1, le=500),
    authorization: Optional[str] = Header(None),
):
    """
    Consulta eventos de um stream temático específico (ex: plantao, locacao, pagamento).
    """
    token = _extract_token(authorization)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de acesso não fornecido.")

    payload = _decode_token(token)
    if not payload or payload.get("role", "user") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito a administradores.")

    if not redis_client:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Redis indisponível.")

    stream_key = f"evt:{domain.lower()}"
    try:
        entries = redis_client.xrevrange(stream_key, count=limit)
        logs = []
        for entry_id, fields in entries:
            try:
                data = json.loads(fields.get("data", "{}"))
                data["stream_id"] = entry_id
                logs.append(data)
            except json.JSONDecodeError:
                logs.append({"stream_id": entry_id, "raw": fields})
        return {"domain": domain, "stream_key": stream_key, "total": len(logs), "logs": logs}
    except Exception as e:
        print(f"[LogService] Erro ao consultar stream temático: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao consultar stream.")


@app.get("/logs/metrics/summary")
async def get_metrics_summary(
    date_str: Optional[str] = None,
    authorization: Optional[str] = Header(None),
):
    """
    Retorna sumário das métricas agregadas diárias para alimentar o painel admin.
    """
    token = _extract_token(authorization)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de acesso não fornecido.")

    payload = _decode_token(token)
    if not payload or payload.get("role", "user") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito a administradores.")

    if not redis_client:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Redis indisponível.")

    target_date = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        keys = redis_client.keys(f"metrics:{target_date}:*")
        metrics = {}
        for k in keys:
            val = redis_client.get(k)
            metric_name = k.replace(f"metrics:{target_date}:", "")
            metrics[metric_name] = int(val) if val and val.isdigit() else 0

        return {"date": target_date, "metrics": metrics}
    except Exception as e:
        print(f"[LogService] Erro ao consultar métricas: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao consultar métricas.")
