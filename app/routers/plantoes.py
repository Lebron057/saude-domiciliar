"""
Roteador de Plantões de Saúde Domiciliar — CuidaHome (Fase 4 / Issue #7).
Contempla o ciclo de contratação direta, mural aberto concorrente, check-in, check-out e avaliações.
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Request, Form, HTTPException, Depends, status
from fastapi.responses import JSONResponse, RedirectResponse

from app.auth import get_current_user
from app.deps import require_roles, require_verified_professional
from app.services.plantoes import (
    criar_plantao,
    aceitar_plantao,
    recusar_plantao,
    realizar_checkin,
    realizar_checkout,
    avaliar_plantao,
    cancelar_plantao,
    ConcurrencyConflictError,
    BusinessRuleError,
)
from app.services.pricing import format_centavos_brl
from app.stripe_service import create_plantao_checkout_session, is_stripe_configured
from app.database import get_connection

router = APIRouter(prefix="/plantoes", tags=["plantoes"])


async def _get_user_or_401(request: Request) -> dict:
    """Helper que extrai usuário ou lança 401."""
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


@router.post("/novo")
async def rota_criar_plantao(
    request: Request,
    paciente_id: int = Form(...),
    modalidade: str = Form(...),
    categoria_exigida: str = Form(...),
    inicio_iso: str = Form(..., alias="inicio"),
    fim_iso: str = Form(..., alias="fim"),
    endereco_atendimento: str = Form(...),
    cidade: str = Form(...),
    uf: str = Form(...),
    profissional_id: Optional[int] = Form(None),
    urgencia: str = Form("agendado"),
    observacoes: Optional[str] = Form(None),
    valor_diaria_centavos: Optional[int] = Form(None),
):
    """
    Criação de solicitação de plantão pelo familiar contratante.
    """
    user = await _get_user_or_401(request)
    if user.get("role") not in ("familiar_paciente", "admin"):
        raise HTTPException(
            status_code=403,
            detail="Apenas familiares ou administradores podem solicitar plantões.",
        )

    try:
        inicio = datetime.fromisoformat(inicio_iso)
        fim = datetime.fromisoformat(fim_iso)
    except Exception:
        raise HTTPException(status_code=400, detail="Formato de data/hora inválido. Use ISO (YYYY-MM-DDTHH:MM).")

    try:
        plantao = criar_plantao(
            familiar_id=user["id"],
            paciente_id=paciente_id,
            modalidade=modalidade,
            categoria_exigida=categoria_exigida,
            inicio=inicio,
            fim=fim,
            endereco_atendimento=endereco_atendimento,
            cidade=cidade,
            uf=uf,
            profissional_id=profissional_id,
            urgencia=urgencia,
            observacoes=observacoes,
            valor_diaria_centavos=valor_diaria_centavos,
        )
        return JSONResponse(status_code=201, content={
            "success": True,
            "plantao": plantao,
            "message": "Plantão solicitado com sucesso.",
        })
    except BusinessRuleError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/mural")
async def rota_listar_mural(
    request: Request,
    cidade: Optional[str] = None,
    uf: Optional[str] = None,
    categoria: Optional[str] = None,
):
    """
    Lista os plantões com status 'aberto' disponíveis no mural para profissionais homologados.
    """
    user = await _get_user_or_401(request)
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
            SELECT p.*, pac.nome as paciente_nome, pac.condicao_resumo, pac.mobilidade
            FROM plantoes p
            JOIN pacientes pac ON p.paciente_id = pac.id
            WHERE p.status = 'aberto' AND p.modalidade = 'mural'
        """
        params = []
        if uf:
            query += " AND p.uf = %s"
            params.append(uf.upper())
        if cidade:
            query += " AND p.cidade = %s"
            params.append(cidade)
        if categoria:
            query += " AND p.categoria_exigida = %s"
            params.append(categoria)

        query += " ORDER BY p.urgencia DESC, p.inicio ASC LIMIT 50"
        cursor.execute(query, tuple(params))
        plantoes = cursor.fetchall()
        return {"plantoes": plantoes, "total": len(plantoes)}
    finally:
        cursor.close()
        conn.close()


@router.get("/meus")
async def rota_meus_plantoes(request: Request):
    """
    Lista os plantões vinculados ao usuário autenticado (como familiar ou profissional).
    """
    user = await _get_user_or_401(request)
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if user.get("role") == "profissional_saude":
            cursor.execute(
                """
                SELECT p.*, pac.nome as paciente_nome, u.nome as familiar_nome, u.telefone as familiar_telefone
                FROM plantoes p
                JOIN pacientes pac ON p.paciente_id = pac.id
                JOIN usuarios u ON p.familiar_id = u.id
                WHERE p.profissional_id = %s
                ORDER BY p.inicio DESC
                """,
                (user["id"],),
            )
        else:  # familiar ou admin
            cursor.execute(
                """
                SELECT p.*, pac.nome as paciente_nome, u.nome as profissional_nome
                FROM plantoes p
                JOIN pacientes pac ON p.paciente_id = pac.id
                LEFT JOIN usuarios u ON p.profissional_id = u.id
                WHERE p.familiar_id = %s
                ORDER BY p.inicio DESC
                """,
                (user["id"],),
            )
        return {"plantoes": cursor.fetchall()}
    finally:
        cursor.close()
        conn.close()


@router.get("/{plantao_id}")
async def rota_obter_plantao(request: Request, plantao_id: int):
    """
    Obtém detalhes de um plantão específico com validação de permissão.
    """
    user = await _get_user_or_401(request)
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT p.*, pac.nome as paciente_nome, pac.condicao_resumo, pac.mobilidade,
                   f.nome as familiar_nome, f.telefone as familiar_telefone,
                   prof.nome as profissional_nome
            FROM plantoes p
            JOIN pacientes pac ON p.paciente_id = pac.id
            JOIN usuarios f ON p.familiar_id = f.id
            LEFT JOIN usuarios prof ON p.profissional_id = prof.id
            WHERE p.id = %s
            """,
            (plantao_id,),
        )
        plantao = cursor.fetchone()
        if not plantao:
            raise HTTPException(status_code=404, detail="Plantão não encontrado.")

        is_admin = (user.get("role") == "admin")
        is_familiar = (user.get("id") == plantao["familiar_id"])
        is_prof = (user.get("id") == plantao["profissional_id"])
        is_open_mural = (plantao["modalidade"] == "mural" and plantao["status"] == "aberto")

        if not (is_admin or is_familiar or is_prof or is_open_mural):
            raise HTTPException(status_code=403, detail="Acesso negado a este plantão.")

        return plantao
    finally:
        cursor.close()
        conn.close()


@router.post("/{plantao_id}/aceitar")
async def rota_aceitar_plantao(request: Request, plantao_id: int):
    """
    Profissional de saúde aceita um plantão (direto ou do mural).
    Critério DoD 1: concorrência no mural aberta tratada com lock atômico -> 409 Conflict se já aceito.
    """
    user = await _get_user_or_401(request)
    if user.get("role") not in ("profissional_saude", "admin"):
        raise HTTPException(
            status_code=403,
            detail="Apenas profissionais de saúde homologados podem aceitar plantões.",
        )

    try:
        plantao = aceitar_plantao(plantao_id=plantao_id, profissional_id=user["id"])
        return {
            "success": True,
            "plantao": plantao,
            "message": "Plantão aceito com sucesso! Aguardando confirmação do pagamento.",
        }
    except ConcurrencyConflictError as ce:
        # DoD 1: 409 Conflict explícito
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(ce))
    except BusinessRuleError as be:
        raise HTTPException(status_code=400, detail=str(be))


@router.post("/{plantao_id}/recusar")
async def rota_recusar_plantao(
    request: Request,
    plantao_id: int,
    motivo: Optional[str] = Form(None),
):
    """
    Profissional recusa uma solicitação direta.
    """
    user = await _get_user_or_401(request)
    try:
        plantao = recusar_plantao(plantao_id=plantao_id, profissional_id=user["id"], motivo=motivo)
        return {
            "success": True,
            "plantao": plantao,
            "message": "Plantão recusado.",
        }
    except BusinessRuleError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{plantao_id}/pagar")
async def rota_pagar_plantao(request: Request, plantao_id: int):
    """
    Familiar inicia o checkout do pagamento da diária via Stripe.
    """
    user = await _get_user_or_401(request)
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM plantoes WHERE id = %s", (plantao_id,))
        plantao = cursor.fetchone()
        if not plantao:
            raise HTTPException(status_code=404, detail="Plantão não encontrado.")

        if plantao["familiar_id"] != user["id"] and user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Apenas o familiar responsável pode realizar o pagamento.")

        if plantao["status"] not in ("solicitado", "aceito", "aguardando_pagamento"):
            raise HTTPException(
                status_code=400,
                detail=f"Plantão no status '{plantao['status']}' não está elegível para pagamento.",
            )

        base_url = str(request.base_url).rstrip("/")
        session = create_plantao_checkout_session(
            plantao_id=plantao_id,
            valor_diaria_centavos=plantao["valor_diaria_centavos"],
            user_email=user.get("email", ""),
            base_url=base_url,
        )

        return {"checkout_url": session.url, "session_id": session.id}
    finally:
        cursor.close()
        conn.close()


@router.post("/{plantao_id}/checkin")
async def rota_checkin(request: Request, plantao_id: int):
    """
    Profissional realiza check-in no início do plantão.
    Critério DoD 3: NÃO é possível realizar check-in se o plantão não estiver confirmado/pago.
    """
    user = await _get_user_or_401(request)
    try:
        plantao = realizar_checkin(plantao_id=plantao_id, profissional_id=user["id"])
        return {
            "success": True,
            "plantao": plantao,
            "message": "Check-in realizado com sucesso! Bom plantão.",
        }
    except BusinessRuleError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{plantao_id}/checkout")
async def rota_checkout(request: Request, plantao_id: int):
    """
    Profissional realiza check-out no término do plantão.
    Libera automaticamente o repasse no ledger para saque.
    """
    user = await _get_user_or_401(request)
    try:
        plantao = realizar_checkout(plantao_id=plantao_id, profissional_id=user["id"])
        return {
            "success": True,
            "plantao": plantao,
            "message": "Check-out realizado com sucesso! O repasse foi liberado para liberação financeira.",
        }
    except BusinessRuleError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{plantao_id}/avaliar")
async def rota_avaliar(
    request: Request,
    plantao_id: int,
    nota: int = Form(...),
    comentario: Optional[str] = Form(None),
):
    """
    Familiar avalia o plantão concluído.
    Critério DoD 4: Avaliação só é permitida após a conclusão ('concluido') do plantão.
    """
    user = await _get_user_or_401(request)
    try:
        avaliacao = avaliar_plantao(
            plantao_id=plantao_id,
            familiar_id=user["id"],
            nota=nota,
            comentario=comentario,
        )
        return {
            "success": True,
            "avaliacao": avaliacao,
            "message": "Avaliação enviada com sucesso! Obrigado pelo feedback.",
        }
    except BusinessRuleError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{plantao_id}/cancelar")
async def rota_cancelar(
    request: Request,
    plantao_id: int,
    motivo: Optional[str] = Form(None),
):
    """
    Familiar ou admin cancela o plantão.
    """
    user = await _get_user_or_401(request)
    try:
        plantao = cancelar_plantao(plantao_id=plantao_id, usuario_id=user["id"], motivo=motivo)
        return {
            "success": True,
            "plantao": plantao,
            "message": "Plantão cancelado com sucesso.",
        }
    except BusinessRuleError as e:
        raise HTTPException(status_code=400, detail=str(e))

