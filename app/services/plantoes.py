"""
Serviço de Gestão do Ciclo de Vida de Plantões e Repasses — CuidaHome.
Implementa a máquina de estados completa:
  aberto (mural) | solicitado (direto)
    -> aceito / aguardando_pagamento
    -> confirmado (após checkout Stripe)
    -> em_andamento (check-in)
    -> concluido (check-out, libera repasse)
    -> cancelado

Segurança & Concorrência:
  - Lock otimista atômico no MariaDB para disputa concorrente de plantões no mural (DoD 1).
  - Cálculo exato em centavos no ledger de repasses (DoD 2).
  - Bloqueio estrito de check-in em plantões não pagos (DoD 3).
  - Bloqueio estrito de avaliação antes da conclusão (DoD 4).
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from app.database import get_connection
from app.services.pricing import (
    calculate_plantao_pricing,
    BASE_DIARIAS_12H,
    BASE_DIARIAS_24H,
)


class ConcurrencyConflictError(Exception):
    """Lançada quando outro profissional aceita o plantão concorrente no mural."""
    pass


class BusinessRuleError(Exception):
    """Lançada quando uma regra de negócio ou transição de estado é violada."""
    pass


def criar_plantao(
    familiar_id: int,
    paciente_id: int,
    modalidade: str,
    categoria_exigida: str,
    inicio: datetime,
    fim: datetime,
    endereco_atendimento: str,
    cidade: str,
    uf: str,
    profissional_id: Optional[int] = None,
    urgencia: str = "agendado",
    observacoes: Optional[str] = None,
    valor_diaria_centavos: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Cria uma nova solicitação de plantão (direto ou mural aberto).
    """
    if fim <= inicio:
        raise BusinessRuleError("O horário de término do plantão deve ser posterior ao início.")

    if modalidade not in ("direto", "mural"):
        raise BusinessRuleError(f"Modalidade inválida: {modalidade}. Use 'direto' ou 'mural'.")

    if categoria_exigida not in ("cuidador", "tecnico_enfermagem", "enfermeiro"):
        raise BusinessRuleError(f"Categoria profissional inválida: {categoria_exigida}.")

    duration_hours = (fim - inicio).total_seconds() / 3600.0

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Validar paciente pertence ao familiar
        cursor.execute("SELECT id, familiar_id FROM pacientes WHERE id = %s", (paciente_id,))
        paciente = cursor.fetchone()
        if not paciente:
            raise BusinessRuleError("Paciente não encontrado.")
        if paciente["familiar_id"] != familiar_id:
            raise BusinessRuleError("Você só pode solicitar plantões para pacientes sob sua responsabilidade.")

        # Calcular diária
        diaria_final = valor_diaria_centavos

        if modalidade == "direto":
            if not profissional_id:
                raise BusinessRuleError("A contratação direta exige a seleção de um profissional específico.")

            cursor.execute(
                """
                SELECT p.usuario_id, p.categoria, p.valor_diaria_12h_centavos,
                       p.valor_diaria_24h_centavos, p.status_verificacao
                FROM perfis_profissionais p
                WHERE p.usuario_id = %s
                """,
                (profissional_id,),
            )
            prof = cursor.fetchone()
            if not prof:
                raise BusinessRuleError("Profissional não encontrado.")
            if prof["status_verificacao"] != "aprovado":
                raise BusinessRuleError("O profissional selecionado ainda não foi homologado para atender plantões.")

            if not diaria_final:
                if duration_hours >= 18 and prof["valor_diaria_24h_centavos"]:
                    diaria_final = prof["valor_diaria_24h_centavos"]
                else:
                    diaria_final = prof["valor_diaria_12h_centavos"]

            status_inicial = "solicitado"

        else:  # mural
            profissional_id = None
            if not diaria_final:
                if duration_hours >= 18:
                    diaria_final = BASE_DIARIAS_24H.get(categoria_exigida, 28000)
                else:
                    diaria_final = BASE_DIARIAS_12H.get(categoria_exigida, 15000)

            status_inicial = "aberto"

        taxa_centavos, repasse_centavos, taxa_percent = calculate_plantao_pricing(diaria_final)

        cursor.execute(
            """
            INSERT INTO plantoes (
                familiar_id, paciente_id, profissional_id, modalidade, urgencia,
                categoria_exigida, inicio, fim, endereco_atendimento, cidade, uf,
                valor_diaria_centavos, taxa_percentual, taxa_centavos, valor_repasse_centavos,
                status, observacoes
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s
            )
            """,
            (
                familiar_id, paciente_id, profissional_id, modalidade, urgencia,
                categoria_exigida, inicio, fim, endereco_atendimento, cidade, uf,
                diaria_final, taxa_percent, taxa_centavos, repasse_centavos,
                status_inicial, observacoes,
            ),
        )
        plantao_id = cursor.lastrowid
        conn.commit()

        cursor.execute("SELECT * FROM plantoes WHERE id = %s", (plantao_id,))
        return cursor.fetchone()

    finally:
        cursor.close()
        conn.close()


def aceitar_plantao(plantao_id: int, profissional_id: int) -> Dict[str, Any]:
    """
    Profissional aceita um plantão.
    - No mural aberto: aplica lock atômico condicional (DoD 1).
    - Na solicitação direta: valida se o profissional é o destinatário.
    Transiciona para status 'aguardando_pagamento'.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Verificar credencial e homologação do profissional
        cursor.execute(
            "SELECT status_verificacao FROM perfis_profissionais WHERE usuario_id = %s",
            (profissional_id,),
        )
        prof = cursor.fetchone()
        if not prof or prof["status_verificacao"] != "aprovado":
            raise BusinessRuleError("Apenas profissionais homologados podem aceitar plantões.")

        cursor.execute("SELECT * FROM plantoes WHERE id = %s", (plantao_id,))
        plantao = cursor.fetchone()
        if not plantao:
            raise BusinessRuleError("Plantão não encontrado.")

        if plantao["modalidade"] == "direto":
            if plantao["profissional_id"] != profissional_id:
                raise BusinessRuleError("Este plantão foi direcionado a outro profissional.")
            if plantao["status"] != "solicitado":
                raise BusinessRuleError(f"Plantão não pode ser aceito no status atual: '{plantao['status']}'.")

            cursor.execute(
                """
                UPDATE plantoes
                SET status = 'aguardando_pagamento', aceito_em = NOW()
                WHERE id = %s AND status = 'solicitado'
                """,
                (plantao_id,),
            )
            conn.commit()

        else:  # modalidade mural: disputa concorrente atômica (DoD 1)
            cursor.execute(
                """
                UPDATE plantoes
                SET profissional_id = %s, status = 'aguardando_pagamento', aceito_em = NOW()
                WHERE id = %s AND status = 'aberto' AND profissional_id IS NULL
                """,
                (profissional_id, plantao_id),
            )
            conn.commit()

            if cursor.rowcount == 0:
                raise ConcurrencyConflictError(
                    "Este plantão já foi aceito por outro profissional ou não está mais aberto no mural."
                )

        cursor.execute("SELECT * FROM plantoes WHERE id = %s", (plantao_id,))
        return cursor.fetchone()

    finally:
        cursor.close()
        conn.close()


def recusar_plantao(plantao_id: int, profissional_id: int, motivo: Optional[str] = None) -> Dict[str, Any]:
    """
    Profissional recusa uma solicitação direta de plantão.
    Transiciona para 'cancelado'.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM plantoes WHERE id = %s", (plantao_id,))
        plantao = cursor.fetchone()
        if not plantao:
            raise BusinessRuleError("Plantão não encontrado.")

        if plantao["profissional_id"] != profissional_id:
            raise BusinessRuleError("Você não tem permissão para recusar este plantão.")

        if plantao["status"] != "solicitado":
            raise BusinessRuleError(f"Não é possível recusar plantão no status '{plantao['status']}'.")

        motivo_final = motivo or "Recusado pelo profissional."
        cursor.execute(
            """
            UPDATE plantoes
            SET status = 'cancelado', cancelado_em = NOW(), motivo_cancelamento = %s
            WHERE id = %s AND status = 'solicitado'
            """,
            (motivo_final, plantao_id),
        )
        conn.commit()

        cursor.execute("SELECT * FROM plantoes WHERE id = %s", (plantao_id,))
        return cursor.fetchone()

    finally:
        cursor.close()
        conn.close()


def confirmar_pagamento_plantao(
    plantao_id: int,
    stripe_session_id: Optional[str] = None,
    stripe_payment_intent_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Chamado pelo Webhook do Stripe (checkout.session.completed com metadata.tipo = 'plantao').
    - Atualiza status para 'confirmado'.
    - Grava linha no ledger 'repasses' com cálculo exato de centavos (DoD 2).
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM plantoes WHERE id = %s", (plantao_id,))
        plantao = cursor.fetchone()
        if not plantao:
            raise BusinessRuleError("Plantão não encontrado.")

        if plantao["status"] not in ("solicitado", "aceito", "aguardando_pagamento"):
            # Idempotência se já confirmado
            if plantao["status"] == "confirmado":
                return plantao
            raise BusinessRuleError(f"Status inválido para confirmação de pagamento: '{plantao['status']}'.")

        cursor.execute(
            """
            UPDATE plantoes
            SET status = 'confirmado',
                stripe_checkout_session_id = %s,
                stripe_payment_intent_id = %s,
                atualizado_em = NOW()
            WHERE id = %s
            """,
            (stripe_session_id, stripe_payment_intent_id, plantao_id),
        )

        # Gravar linha no ledger de repasses para o profissional (DoD 2)
        if plantao["profissional_id"]:
            cursor.execute(
                """
                INSERT IGNORE INTO repasses (
                    beneficiario_id, origem_tipo, origem_id,
                    valor_bruto_centavos, taxa_plataforma_centavos, valor_liquido_centavos,
                    status
                ) VALUES (
                    %s, 'plantao', %s,
                    %s, %s, %s,
                    'pendente'
                )
                """,
                (
                    plantao["profissional_id"], plantao_id,
                    plantao["valor_diaria_centavos"],
                    plantao["taxa_centavos"],
                    plantao["valor_repasse_centavos"],
                ),
            )

        conn.commit()
        cursor.execute("SELECT * FROM plantoes WHERE id = %s", (plantao_id,))
        return cursor.fetchone()

    finally:
        cursor.close()
        conn.close()


def realizar_checkin(plantao_id: int, profissional_id: int) -> Dict[str, Any]:
    """
    Profissional inicia o atendimento domiciliar.
    Critério DoD 3: NÃO é permitido realizar check-in em plantão não pago ('confirmado').
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM plantoes WHERE id = %s", (plantao_id,))
        plantao = cursor.fetchone()
        if not plantao:
            raise BusinessRuleError("Plantão não encontrado.")

        if plantao["profissional_id"] != profissional_id:
            raise BusinessRuleError("Você não é o profissional designado para este plantão.")

        if plantao["status"] != "confirmado":
            raise BusinessRuleError(
                f"Não é possível realizar check-in em plantão com status '{plantao['status']}'. "
                "O plantão precisa estar pago e com status 'confirmado'."
            )

        cursor.execute(
            """
            UPDATE plantoes
            SET status = 'em_andamento', checkin_em = NOW()
            WHERE id = %s AND status = 'confirmado'
            """,
            (plantao_id,),
        )
        conn.commit()

        cursor.execute("SELECT * FROM plantoes WHERE id = %s", (plantao_id,))
        return cursor.fetchone()

    finally:
        cursor.close()
        conn.close()


def realizar_checkout(plantao_id: int, profissional_id: int) -> Dict[str, Any]:
    """
    Profissional finaliza o plantão domiciliar.
    - Transiciona para 'concluido'.
    - Libera automaticamente o repasse financeiro ('status = liberado') no ledger.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM plantoes WHERE id = %s", (plantao_id,))
        plantao = cursor.fetchone()
        if not plantao:
            raise BusinessRuleError("Plantão não encontrado.")

        if plantao["profissional_id"] != profissional_id:
            raise BusinessRuleError("Você não é o profissional designado para este plantão.")

        if plantao["status"] != "em_andamento":
            raise BusinessRuleError(
                f"Check-out só pode ser realizado em plantões em andamento. Status atual: '{plantao['status']}'."
            )

        cursor.execute(
            """
            UPDATE plantoes
            SET status = 'concluido', checkout_em = NOW()
            WHERE id = %s AND status = 'em_andamento'
            """,
            (plantao_id,),
        )

        # Liberar repasse no ledger para o profissional
        cursor.execute(
            """
            UPDATE repasses
            SET status = 'liberado'
            WHERE origem_tipo = 'plantao' AND origem_id = %s AND status = 'pendente'
            """,
            (plantao_id,),
        )

        conn.commit()
        cursor.execute("SELECT * FROM plantoes WHERE id = %s", (plantao_id,))
        return cursor.fetchone()

    finally:
        cursor.close()
        conn.close()


def avaliar_plantao(
    plantao_id: int,
    familiar_id: int,
    nota: int,
    comentario: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Familiar avalia o atendimento do profissional.
    Critério DoD 4: Avaliação permitida APENAS se o plantão estiver no estado 'concluido'.
    """
    if nota < 1 or nota > 5:
        raise BusinessRuleError("A nota de avaliação deve estar entre 1 e 5 estrelas.")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM plantoes WHERE id = %s", (plantao_id,))
        plantao = cursor.fetchone()
        if not plantao:
            raise BusinessRuleError("Plantão não encontrado.")

        if plantao["familiar_id"] != familiar_id:
            raise BusinessRuleError("Apenas o familiar contratante pode avaliar este plantão.")

        # DoD 4: bloqueio estrito se não concluído
        if plantao["status"] != "concluido":
            raise BusinessRuleError(
                f"Avaliação permitida apenas após a conclusão do plantão. Status atual: '{plantao['status']}'."
            )

        prof_id = plantao["profissional_id"]
        if not prof_id:
            raise BusinessRuleError("Plantão não possui profissional atribuído para avaliação.")

        # Verificar se já avaliou
        cursor.execute("SELECT id FROM avaliacoes WHERE plantao_id = %s", (plantao_id,))
        if cursor.fetchone():
            raise BusinessRuleError("Este plantão já foi avaliado anteriormente.")

        cursor.execute(
            """
            INSERT INTO avaliacoes (plantao_id, usuario_id, profissional_id, nota, comentario)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (plantao_id, familiar_id, prof_id, nota, comentario.strip() if comentario else None),
        )
        avaliacao_id = cursor.lastrowid

        # Recalcular nota média e total de avaliações no perfil profissional
        cursor.execute(
            """
            SELECT AVG(nota) as media, COUNT(*) as total
            FROM avaliacoes
            WHERE profissional_id = %s AND status_moderacao != 'rejeitado'
            """,
            (prof_id,),
        )
        stats = cursor.fetchone()
        media = round(float(stats["media"]), 2) if stats and stats["media"] else 0.0
        total = stats["total"] if stats else 0

        cursor.execute(
            """
            UPDATE perfis_profissionais
            SET nota_media = %s, total_avaliacoes = %s
            WHERE usuario_id = %s
            """,
            (media, total, prof_id),
        )

        conn.commit()
        return {
            "id": avaliacao_id,
            "plantao_id": plantao_id,
            "profissional_id": prof_id,
            "nota": nota,
            "comentario": comentario,
            "nota_media_atualizada": media,
            "total_avaliacoes": total,
        }

    finally:
        cursor.close()
        conn.close()


def cancelar_plantao(plantao_id: int, usuario_id: int, motivo: Optional[str] = None) -> Dict[str, Any]:
    """
    Familiar cancela uma solicitação de plantão.
    Se já concluído, não pode cancelar.
    Se pago, estorna o repasse pendente.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM plantoes WHERE id = %s", (plantao_id,))
        plantao = cursor.fetchone()
        if not plantao:
            raise BusinessRuleError("Plantão não encontrado.")

        cursor.execute("SELECT role FROM usuarios WHERE id = %s", (usuario_id,))
        user_row = cursor.fetchone()
        is_admin = (user_row and user_row.get("role") == "admin")
        is_familiar = (plantao["familiar_id"] == usuario_id)

        if not (is_admin or is_familiar):
            raise BusinessRuleError("Apenas o familiar contratante ou administradores podem cancelar este plantão.")

        if plantao["status"] in ("concluido", "cancelado"):
            raise BusinessRuleError(f"Plantão não pode ser cancelado no status atual: '{plantao['status']}'.")

        motivo_final = motivo or "Cancelado pelo cliente/familiar."
        cursor.execute(
            """
            UPDATE plantoes
            SET status = 'cancelado', cancelado_em = NOW(), motivo_cancelamento = %s
            WHERE id = %s
            """,
            (motivo_final, plantao_id),
        )

        # Se houver repasse gerado, estorna no ledger
        cursor.execute(
            """
            UPDATE repasses
            SET status = 'estornado'
            WHERE origem_tipo = 'plantao' AND origem_id = %s AND status = 'pendente'
            """,
            (plantao_id,),
        )

        conn.commit()
        cursor.execute("SELECT * FROM plantoes WHERE id = %s", (plantao_id,))
        return cursor.fetchone()

    finally:
        cursor.close()
        conn.close()
