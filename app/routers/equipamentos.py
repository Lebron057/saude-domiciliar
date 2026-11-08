"""
Roteador do Catálogo de Equipamentos e Locações — CuidaHome (Fase 5 / Issue #8).
Contempla vitrine, consulta de estoque em tempo real, contratação de locação recorrente e vistorias.
"""

from datetime import datetime, date
from typing import Optional
try:
    from fastapi import APIRouter, Request, Form, HTTPException, status
    from fastapi.responses import JSONResponse, RedirectResponse
except ImportError:
    class HTTPException(Exception):
        def __init__(self, status_code: int = 500, detail: str = ""):
            self.status_code = status_code
            self.detail = detail
            super().__init__(f"HTTP {status_code}: {detail}")
    class APIRouter:
        def __init__(self, *a, **kw): pass
        def get(self, *a, **kw): return lambda f: f
        def post(self, *a, **kw): return lambda f: f
    class Request: pass
    def Form(default=None, **kw): return default
    class JSONResponse:
        def __init__(self, content=None, status_code=200): self.content = content; self.status_code = status_code
    class RedirectResponse:
        def __init__(self, url=None, status_code=303): self.url = url; self.status_code = status_code
    class status:
        HTTP_400_BAD_REQUEST = 400
        HTTP_401_UNAUTHORIZED = 401
        HTTP_403_FORBIDDEN = 403
        HTTP_404_NOT_FOUND = 404

from app.auth import get_current_user
from app.services.locacoes import (
    solicitar_locacao,
    solicitar_devolucao_locacao,
    realizar_vistoria_e_encerramento,
    verificar_disponibilidade_estoque,
    BusinessRuleError,
)
from app.stripe_service import create_subscription_checkout_session
from app.database import get_connection

router = APIRouter(tags=["equipamentos_locacoes"])


async def _get_user_or_401(request: Request) -> dict:
    try:
        user = await get_current_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Autenticação obrigatória.")
        return user
    except Exception:
        raise HTTPException(status_code=401, detail="Autenticação obrigatória.")


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


@router.get("/api/equipamentos")
async def listar_equipamentos_api(categoria: Optional[str] = None):
    """
    Retorna o catálogo de equipamentos ativos com dados de categoria e disponibilidade de estoque.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
            SELECT eq.*, cat.nome as categoria_nome, cat.slug as categoria_slug,
                   (SELECT COUNT(*) FROM unidades_equipamento u WHERE u.equipamento_id = eq.id AND u.status = 'disponivel') as estoque_disponivel
            FROM equipamentos eq
            JOIN categorias_equipamento cat ON eq.categoria_id = cat.id
            WHERE eq.ativo = TRUE
        """
        params = []
        if categoria:
            query += " AND cat.slug = %s"
            params.append(categoria)

        query += " ORDER BY eq.preco_mensal_centavos ASC"
        cursor.execute(query, tuple(params))
        items = cursor.fetchall()
        return {"equipamentos": items, "total": len(items)}
    finally:
        cursor.close()
        conn.close()


@router.get("/api/equipamentos/{equipamento_id}")
async def obter_equipamento_api(equipamento_id: int):
    """
    Retorna os detalhes de um equipamento específico.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT eq.*, cat.nome as categoria_nome, cat.slug as categoria_slug,
                   (SELECT COUNT(*) FROM unidades_equipamento u WHERE u.equipamento_id = eq.id AND u.status = 'disponivel') as estoque_disponivel
            FROM equipamentos eq
            JOIN categorias_equipamento cat ON eq.categoria_id = cat.id
            WHERE eq.id = %s
            """,
            (equipamento_id,),
        )
        eq = cursor.fetchone()
        if not eq:
            raise HTTPException(status_code=404, detail="Equipamento não encontrado.")
        return eq
    finally:
        cursor.close()
        conn.close()


@router.post("/equipamentos/{equipamento_id}/locar")
async def rota_locar_equipamento(
    request: Request,
    equipamento_id: int,
    endereco_entrega: str = Form(...),
    cidade: str = Form(...),
    uf: str = Form(...),
    data_entrega_prevista_str: str = Form(..., alias="data_entrega_prevista"),
    aceite_termo: bool = Form(False),
    paciente_id: Optional[int] = Form(None),
    periodo_previsto_dias: int = Form(30),
):
    """
    Inicia o fluxo de contratação de locação recorrente com Stripe Billing e caução.
    Critério DoD 4: Rejeita com mensagem de indisponibilidade caso não haja unidades em estoque.
    """
    user = await _get_user_or_401(request)

    if not aceite_termo:
        raise HTTPException(
            status_code=400,
            detail="É obrigatório concordar com os termos de locação e política de caução para prosseguir.",
        )

    try:
        data_entrega = date.fromisoformat(data_entrega_prevista_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Data de entrega prevista inválida (use YYYY-MM-DD).")

    client_ip = _get_client_ip(request)

    try:
        locacao = solicitar_locacao(
            cliente_id=user["id"],
            equipamento_id=equipamento_id,
            endereco_entrega=endereco_entrega,
            cidade=cidade,
            uf=uf,
            data_entrega_prevista=data_entrega,
            aceite_termo=aceite_termo,
            client_ip=client_ip,
            paciente_id=paciente_id,
            periodo_previsto_dias=periodo_previsto_dias,
        )

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT stripe_price_id FROM equipamentos WHERE id = %s", (equipamento_id,))
            eq = cursor.fetchone()
            stripe_price_id = eq["stripe_price_id"] if eq and eq["stripe_price_id"] else "price_mock_padrao"
        finally:
            cursor.close()
            conn.close()

        base_url = str(request.base_url).rstrip("/")
        session = create_subscription_checkout_session(
            locacao_id=locacao["id"],
            stripe_price_id=stripe_price_id,
            cliente_id=user["id"],
            user_email=user.get("email", ""),
            base_url=base_url,
        )

        # Se submissão de formulário HTML pelo navegador, redireciona diretamente ao checkout
        if "text/html" in request.headers.get("accept", "") and getattr(session, "url", None):
            return RedirectResponse(url=session.url, status_code=303)

        return {
            "success": True,
            "locacao_id": locacao["id"],
            "checkout_url": session.url,
            "session_id": session.id,
            "message": "Solicitação registrada. Redirecionando para o checkout seguro da Stripe.",
        }

    except BusinessRuleError as be:
        # DoD 4: Mensagem amigável de indisponibilidade / regra de negócio
        raise HTTPException(status_code=400, detail=str(be))


@router.get("/locacoes/minhas")
async def rota_minhas_locacoes(request: Request):
    """
    Retorna as locações do cliente logado.
    """
    user = await _get_user_or_401(request)
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT l.*, eq.nome as equipamento_nome, eq.preco_mensal_centavos,
                   c.status as caucao_status, c.valor_centavos as caucao_valor_centavos
            FROM locacoes l
            JOIN equipamentos eq ON l.equipamento_id = eq.id
            LEFT JOIN caucoes c ON l.id = c.locacao_id
            WHERE l.cliente_id = %s
            ORDER BY l.criado_em DESC
            """,
            (user["id"],),
        )
        return {"locacoes": cursor.fetchall()}
    finally:
        cursor.close()
        conn.close()


@router.post("/locacoes/{locacao_id}/devolver")
async def rota_solicitar_devolucao(request: Request, locacao_id: int):
    """
    Cliente solicita a devolução e encerramento do aluguel.
    """
    user = await _get_user_or_401(request)
    try:
        locacao = solicitar_devolucao_locacao(locacao_id=locacao_id, cliente_id=user["id"])
        return {
            "success": True,
            "locacao": locacao,
            "message": "Solicitação de devolução registrada com sucesso. O fornecedor agendará o recolhimento.",
        }
    except BusinessRuleError as be:
        raise HTTPException(status_code=400, detail=str(be))


@router.post("/locacoes/{locacao_id}/vistoria")
async def rota_vistoria_locacao(
    request: Request,
    locacao_id: int,
    aprovado_sem_avarias: bool = Form(...),
    observacoes: Optional[str] = Form(None),
    foto_vistoria_key: Optional[str] = Form(None),
):
    """
    Fornecedor ou admin registra a vistoria após recolhimento.
    Critério DoD 3: Vistoria aprovada cancela o hold da caução sem cobrar nada do cliente.
    """
    user = await _get_user_or_401(request)
    if user.get("role") not in ("fornecedor_equipamento", "admin"):
        raise HTTPException(
            status_code=403,
            detail="Apenas fornecedores ou administradores podem registrar vistorias.",
        )

    try:
        locacao = realizar_vistoria_e_encerramento(
            locacao_id=locacao_id,
            responsavel_id=user["id"],
            aprovado_sem_avarias=aprovado_sem_avarias,
            observacoes=observacoes,
            foto_vistoria_key=foto_vistoria_key,
        )
        msg = "Vistoria aprovada! A caução foi liberada e a locação foi encerrada." if aprovado_sem_avarias else "Vistoria com avaria registrada para apuração de danos."
        return {
            "success": True,
            "locacao": locacao,
            "message": msg,
        }
    except BusinessRuleError as be:
        raise HTTPException(status_code=400, detail=str(be))

