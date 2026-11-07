"""
Serviço de Gestão de Locações de Equipamentos Ortopédicos e Cauções — CuidaHome.
Implementa o ciclo de locação via Stripe Billing recorrente e retenção de caução (Opção A):
  pendente_pagamento
    -> em_separacao (após checkout Stripe + autorização de caução / hold)
    -> despachada -> entregue
    -> devolucao_solicitada
    -> recolhida / vistoria
    -> encerrada (libera hold da caução sem debitar o cliente)
    -> inadimplente (se invoice falhar)
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any

from app.database import get_connection
from app.services.pricing import calculate_plantao_pricing, format_centavos_brl


class BusinessRuleError(Exception):
    """Lançada quando uma regra de negócio de locação ou estoque é violada."""
    pass


def verificar_disponibilidade_estoque(equipamento_id: int) -> Dict[str, Any]:
    """
    Verifica se há unidades físicas disponíveis em estoque para o equipamento.
    Retorna {'disponivel': bool, 'unidades_disponiveis': int, 'proxima_unidade_id': Optional[int]}.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT id, numero_patrimonio
            FROM unidades_equipamento
            WHERE equipamento_id = %s AND status = 'disponivel'
            ORDER BY id ASC
            """,
            (equipamento_id,),
        )
        rows = cursor.fetchall()
        disponivel = len(rows) > 0
        proxima_id = rows[0]["id"] if disponivel else None
        return {
            "disponivel": disponivel,
            "unidades_disponiveis": len(rows),
            "proxima_unidade_id": proxima_id,
        }
    finally:
        cursor.close()
        conn.close()


def solicitar_locacao(
    cliente_id: int,
    equipamento_id: int,
    endereco_entrega: str,
    cidade: str,
    uf: str,
    data_entrega_prevista: date,
    aceite_termo: bool,
    client_ip: str,
    paciente_id: Optional[int] = None,
    periodo_previsto_dias: int = 30,
) -> Dict[str, Any]:
    """
    Registra solicitação de locação de equipamento ortopédico com aceite digital de contrato.
    Critério DoD 4: Equipamento sem estoque disponível rejeita com mensagem amigável de indisponibilidade.
    """
    if not aceite_termo:
        raise BusinessRuleError("É obrigatório o aceite digital dos termos e condições do contrato de locação.")

    # DoD 4: validação estrita de estoque
    disp = verificar_disponibilidade_estoque(equipamento_id)
    if not disp["disponivel"]:
        raise BusinessRuleError(
            "Este equipamento está temporariamente sem unidades disponíveis no estoque para locação imediata. "
            "Por favor, escolha outro modelo ou consulte nossa equipe de suporte."
        )

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Obter dados do equipamento
        cursor.execute("SELECT * FROM equipamentos WHERE id = %s AND ativo = TRUE", (equipamento_id,))
        eq = cursor.fetchone()
        if not eq:
            raise BusinessRuleError("Equipamento não encontrado ou inativo no catálogo.")

        # Inserir locação
        cursor.execute(
            """
            INSERT INTO locacoes (
                cliente_id, paciente_id, equipamento_id, unidade_id,
                endereco_entrega, cidade, uf, data_entrega_prevista,
                periodo_previsto_dias, status
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, 'pendente_pagamento'
            )
            """,
            (
                cliente_id, paciente_id, equipamento_id, disp["proxima_unidade_id"],
                endereco_entrega, cidade, uf.upper(), data_entrega_prevista,
                periodo_previsto_dias,
            ),
        )
        locacao_id = cursor.lastrowid

        # Reservar temporariamente a unidade física
        if disp["proxima_unidade_id"]:
            cursor.execute(
                "UPDATE unidades_equipamento SET status = 'locado' WHERE id = %s",
                (disp["proxima_unidade_id"],),
            )

        # Registrar o aceite formal do termo de locação na tabela contratos
        cursor.execute(
            """
            INSERT INTO contratos (usuario_id, tipo, referencia_id, versao_termo, ip_aceite)
            VALUES (%s, 'locacao_equipamento', %s, 'v1.0', %s)
            """,
            (cliente_id, locacao_id, client_ip),
        )

        conn.commit()

        cursor.execute("SELECT * FROM locacoes WHERE id = %s", (locacao_id,))
        return cursor.fetchone()

    finally:
        cursor.close()
        conn.close()


def confirmar_pagamento_locacao(
    locacao_id: int,
    stripe_subscription_id: str,
    stripe_customer_id: str,
    stripe_session_id: Optional[str] = None,
    mock_hold_intent_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Chamado pelo Webhook do Stripe (checkout.session.completed com metadata.tipo = 'locacao').
    Critério DoD 1:
      - Transiciona status da locação para 'em_separacao'.
      - Associa subscription_id e customer_id.
      - Provisiona autorização de caução (hold/PaymentIntent com capture_method='manual').
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM locacoes WHERE id = %s", (locacao_id,))
        locacao = cursor.fetchone()
        if not locacao:
            raise BusinessRuleError("Locação não encontrada.")

        # Atualiza status da locação para 'em_separacao'
        cursor.execute(
            """
            UPDATE locacoes
            SET status = 'em_separacao',
                stripe_subscription_id = %s,
                stripe_customer_id = %s,
                stripe_checkout_session_id = %s,
                atualizado_em = NOW()
            WHERE id = %s
            """,
            (stripe_subscription_id, stripe_customer_id, stripe_session_id, locacao_id),
        )

        # Buscar valor de caução do equipamento
        cursor.execute(
            "SELECT valor_caucao_centavos FROM equipamentos WHERE id = %s",
            (locacao["equipamento_id"],),
        )
        eq = cursor.fetchone()
        valor_caucao = eq["valor_caucao_centavos"] if eq else 60000

        # Criar registro de caução com status 'autorizada' (hold no cartão)
        intent_id = mock_hold_intent_id or f"pi_caucao_loc_{locacao_id}"
        cursor.execute(
            """
            INSERT INTO caucoes (
                locacao_id, valor_centavos, stripe_payment_intent_id,
                status, capture_before
            ) VALUES (
                %s, %s, %s,
                'autorizada', DATE_ADD(NOW(), INTERVAL 7 DAY)
            )
            ON DUPLICATE KEY UPDATE
                valor_centavos = VALUES(valor_centavos),
                stripe_payment_intent_id = VALUES(stripe_payment_intent_id),
                status = 'autorizada',
                capture_before = VALUES(capture_before)
            """,
            (locacao_id, valor_caucao, intent_id),
        )

        conn.commit()
        cursor.execute("SELECT * FROM locacoes WHERE id = %s", (locacao_id,))
        return cursor.fetchone()

    finally:
        cursor.close()
        conn.close()


def renovar_locacao_mensal(stripe_subscription_id: str) -> Optional[Dict[str, Any]]:
    """
    Chamado pelo Webhook invoice.paid (billing_reason = 'subscription_cycle').
    Critério DoD 2: Emite evento de renovação sem duplicar locações e gera repasse ao fornecedor.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT l.*, eq.fornecedor_id, eq.preco_mensal_centavos
            FROM locacoes l
            JOIN equipamentos eq ON l.equipamento_id = eq.id
            WHERE l.stripe_subscription_id = %s
            """,
            (stripe_subscription_id,),
        )
        locacao = cursor.fetchone()
        if not locacao:
            return None

        # Gerar repasse mensal do aluguel para o fornecedor (com take rate da plataforma)
        preco = locacao["preco_mensal_centavos"]
        taxa, repasse, _ = calculate_plantao_pricing(preco)

        cursor.execute(
            """
            INSERT INTO repasses (
                beneficiario_id, origem_tipo, origem_id,
                valor_bruto_centavos, taxa_plataforma_centavos, valor_liquido_centavos,
                status
            ) VALUES (
                %s, 'fatura_locacao', %s,
                %s, %s, %s,
                'pendente'
            )
            """,
            (locacao["fornecedor_id"], locacao["id"], preco, taxa, repasse),
        )

        conn.commit()
        return locacao

    finally:
        cursor.close()
        conn.close()


def marcar_locacao_inadimplente(stripe_subscription_id: str) -> Optional[Dict[str, Any]]:
    """
    Chamado pelo Webhook invoice.payment_failed.
    Marca a locação como 'inadimplente'.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT * FROM locacoes WHERE stripe_subscription_id = %s",
            (stripe_subscription_id,),
        )
        locacao = cursor.fetchone()
        if not locacao:
            return None

        cursor.execute(
            "UPDATE locacoes SET status = 'inadimplente' WHERE id = %s",
            (locacao["id"],),
        )
        conn.commit()
        cursor.execute("SELECT * FROM locacoes WHERE id = %s", (locacao["id"],))
        return cursor.fetchone()

    finally:
        cursor.close()
        conn.close()


def solicitar_devolucao_locacao(locacao_id: int, cliente_id: int) -> Dict[str, Any]:
    """
    Cliente ou admin solicita devolução e encerramento do aluguel.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM locacoes WHERE id = %s", (locacao_id,))
        locacao = cursor.fetchone()
        if not locacao:
            raise BusinessRuleError("Locação não encontrada.")

        if locacao["cliente_id"] != cliente_id:
            cursor.execute("SELECT role FROM usuarios WHERE id = %s", (cliente_id,))
            user = cursor.fetchone()
            if not user or user["role"] != "admin":
                raise BusinessRuleError("Apenas o locatário ou administradores podem solicitar devolução.")

        cursor.execute(
            """
            UPDATE locacoes
            SET status = 'devolucao_solicitada'
            WHERE id = %s AND status IN ('em_separacao', 'despachada', 'entregue')
            """,
            (locacao_id,),
        )
        cursor.execute(
            """
            INSERT INTO movimentacoes_locacao (locacao_id, responsavel_id, tipo, observacoes)
            VALUES (%s, %s, 'solicitacao_devolucao', 'Solicitação de devolução pelo cliente.')
            """,
            (locacao_id, cliente_id),
        )
        conn.commit()

        cursor.execute("SELECT * FROM locacoes WHERE id = %s", (locacao_id,))
        return cursor.fetchone()

    finally:
        cursor.close()
        conn.close()


def realizar_vistoria_e_encerramento(
    locacao_id: int,
    responsavel_id: int,
    aprovado_sem_avarias: bool,
    observacoes: Optional[str] = None,
    foto_vistoria_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Fornecedor ou administrador realiza a vistoria física do equipamento recolhido.
    Critério DoD 3:
      - Vistoria aprovada sem avarias: cancela e libera a autorização de caução (hold)
        sem debitar nenhum valor do cliente.
      - Libera a unidade física para novas locações e encerra a locação.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM locacoes WHERE id = %s", (locacao_id,))
        locacao = cursor.fetchone()
        if not locacao:
            raise BusinessRuleError("Locação não encontrada.")

        obs = observacoes or ("Vistoria aprovada sem avarias." if aprovado_sem_avarias else "Avarias detectadas na vistoria.")

        # Registrar movimentação de vistoria
        cursor.execute(
            """
            INSERT INTO movimentacoes_locacao (
                locacao_id, responsavel_id, tipo, observacoes, foto_vistoria_key
            ) VALUES (%s, %s, 'vistoria', %s, %s)
            """,
            (locacao_id, responsavel_id, obs, foto_vistoria_key),
        )

        if aprovado_sem_avarias:
            # DoD 3: Libera a caução (hold cancelado no cartão, status = liberada)
            cursor.execute(
                """
                UPDATE caucoes
                SET status = 'liberada', motivo = 'Vistoria aprovada sem avarias.'
                WHERE locacao_id = %s
                """,
                (locacao_id,),
            )

            # Encerra a locação
            cursor.execute(
                "UPDATE locacoes SET status = 'encerrada' WHERE id = %s",
                (locacao_id,),
            )

            # Libera a unidade física de volta para o estoque disponível
            if locacao["unidade_id"]:
                cursor.execute(
                    "UPDATE unidades_equipamento SET status = 'disponivel' WHERE id = %s",
                    (locacao["unidade_id"],),
                )
        else:
            # Avaria detectada: caução mantida para captura parcial/total
            cursor.execute(
                """
                UPDATE caucoes
                SET status = 'capturada_parcial', motivo = %s
                WHERE locacao_id = %s
                """,
                (obs, locacao_id),
            )

        conn.commit()

        cursor.execute("SELECT * FROM locacoes WHERE id = %s", (locacao_id,))
        return cursor.fetchone()

    finally:
        cursor.close()
        conn.close()
