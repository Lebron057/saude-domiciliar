"""
Testes Unitários da Fase 4 — Ciclo de Plantões, Concorrência no Mural e Repasses.
Cobre todos os critérios de aceitação (DoD 1 a 4) da Issue #7 / Atividade 9.
"""

from datetime import datetime, timedelta
import unittest
from unittest.mock import MagicMock, patch, call

from app.services.pricing import (
    calculate_plantao_pricing,
    format_centavos_brl,
    get_platform_fee_percent,
    BASE_DIARIAS_12H,
    BASE_DIARIAS_24H,
)
from app.services.plantoes import (
    criar_plantao,
    aceitar_plantao,
    recusar_plantao,
    confirmar_pagamento_plantao,
    realizar_checkin,
    realizar_checkout,
    avaliar_plantao,
    cancelar_plantao,
    ConcurrencyConflictError,
    BusinessRuleError,
)


class TestPricingCalculations(unittest.TestCase):
    """Testes da camada de cálculo de taxas e split financeiro em centavos."""

    def test_calculate_plantao_pricing_exact(self):
        # Diária R$ 150,00 (15000 centavos) com taxa padrão de 12%
        taxa, repasse, percent = calculate_plantao_pricing(15000, fee_percent=12.0)
        self.assertEqual(percent, 12.0)
        self.assertEqual(taxa, 1800)        # R$ 18,00
        self.assertEqual(repasse, 13200)    # R$ 132,00
        # Invariante estrita: taxa + repasse = diária
        self.assertEqual(taxa + repasse, 15000)

    def test_calculate_plantao_pricing_custom_take_rate(self):
        # Diária R$ 280,00 (28000 centavos) com taxa de 15%
        taxa, repasse, percent = calculate_plantao_pricing(28000, fee_percent=15.0)
        self.assertEqual(taxa, 4200)        # R$ 42,00
        self.assertEqual(repasse, 23800)    # R$ 238,00
        self.assertEqual(taxa + repasse, 28000)

    def test_calculate_pricing_rejects_negative_or_zero(self):
        with self.assertRaises(ValueError):
            calculate_plantao_pricing(0)
        with self.assertRaises(ValueError):
            calculate_plantao_pricing(-500)

    def test_calculate_pricing_rejects_invalid_fee(self):
        with self.assertRaises(ValueError):
            calculate_plantao_pricing(10000, fee_percent=-1)
        with self.assertRaises(ValueError):
            calculate_plantao_pricing(10000, fee_percent=101)

    def test_format_centavos_brl(self):
        self.assertEqual(format_centavos_brl(15000), "R$ 150,00")
        self.assertEqual(format_centavos_brl(28000), "R$ 280,00")
        self.assertEqual(format_centavos_brl(14900), "R$ 149,00")
        self.assertEqual(format_centavos_brl(99), "R$ 0,99")


class TestPlantoesConcurrencyAndLifecycle(unittest.TestCase):
    """Testes dos critérios de aceitação DoD 1, DoD 2, DoD 3 e DoD 4."""

    @patch("app.services.plantoes.get_connection")
    def test_dod1_mural_concurrency_race_condition(self, mock_get_conn):
        """
        Critério DoD 1:
        Em concorrência simultânea para aceitar plantão no mural aberto:
        - 1º profissional atualiza com sucesso (rowcount=1 -> OK).
        - Os demais 4 recebem ConcurrencyConflictError (HTTP 409 Conflict).
        """
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Simular profissional aprovado
        mock_cursor.fetchone.side_effect = [
            {"status_verificacao": "aprovado"},   # verificação do prof
            {"id": 100, "modalidade": "mural", "status": "aberto", "profissional_id": None},  # plantao
            {"id": 100, "status": "aguardando_pagamento", "profissional_id": 10},               # retorno final
        ]

        # 1ª tentativa: ganha a disputa (rowcount = 1)
        mock_cursor.rowcount = 1
        res = aceitar_plantao(plantao_id=100, profissional_id=10)
        self.assertEqual(res["status"], "aguardando_pagamento")

        # 2ª a 5ª tentativa: perdem a disputa (rowcount = 0)
        mock_cursor.fetchone.side_effect = [
            {"status_verificacao": "aprovado"},
            {"id": 100, "modalidade": "mural", "status": "aberto", "profissional_id": None},
        ]
        mock_cursor.rowcount = 0
        with self.assertRaises(ConcurrencyConflictError) as ctx:
            aceitar_plantao(plantao_id=100, profissional_id=11)
        self.assertIn("já foi aceito por outro profissional", str(ctx.exception))

        with self.assertRaises(ConcurrencyConflictError):
            mock_cursor.fetchone.side_effect = [
                {"status_verificacao": "aprovado"},
                {"id": 100, "modalidade": "mural", "status": "aberto", "profissional_id": None},
            ]
            aceitar_plantao(plantao_id=100, profissional_id=12)

    @patch("app.services.plantoes.get_connection")
    def test_dod2_webhook_stripe_confirms_shift_and_creates_repasse(self, mock_get_conn):
        """
        Critério DoD 2:
        O webhook da Stripe marca o plantão como 'confirmado' e grava a linha no ledger
        'repasses' com o cálculo exato de centavos.
        """
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        plantao_mock = {
            "id": 55,
            "profissional_id": 20,
            "valor_diaria_centavos": 20000,
            "taxa_centavos": 2400,
            "valor_repasse_centavos": 17600,
            "status": "aguardando_pagamento",
        }
        confirmed_mock = dict(plantao_mock, status="confirmado")

        mock_cursor.fetchone.side_effect = [plantao_mock, confirmed_mock]

        res = confirmar_pagamento_plantao(
            plantao_id=55,
            stripe_session_id="cs_test_123",
            stripe_payment_intent_id="pi_test_456",
        )
        self.assertEqual(res["status"], "confirmado")

        # Verificar se executou INSERT na tabela repasses com valores exatos
        executed_sqls = [c[0][0] for c in mock_cursor.execute.call_args_list]
        self.assertTrue(any("INSERT IGNORE INTO repasses" in sql for sql in executed_sqls))

        # Encontrar a chamada do repasse
        repasse_call = [c for c in mock_cursor.execute.call_args_list if "INSERT IGNORE INTO repasses" in c[0][0]][0]
        params = repasse_call[0][1]
        self.assertEqual(params[0], 20)      # beneficiario_id (profissional)
        self.assertEqual(params[1], 55)      # plantao_id
        self.assertEqual(params[2], 20000)   # valor_bruto_centavos
        self.assertEqual(params[3], 2400)    # taxa_plataforma_centavos
        self.assertEqual(params[4], 17600)   # valor_liquido_centavos

    @patch("app.services.plantoes.get_connection")
    def test_dod3_checkin_blocked_on_unpaid_shift(self, mock_get_conn):
        """
        Critério DoD 3:
        Não é possível realizar check-in em plantão não pago ('confirmado').
        """
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Plantão ainda no status 'aguardando_pagamento'
        mock_cursor.fetchone.return_value = {
            "id": 77,
            "profissional_id": 30,
            "status": "aguardando_pagamento",
        }

        with self.assertRaises(BusinessRuleError) as ctx:
            realizar_checkin(plantao_id=77, profissional_id=30)
        self.assertIn("confirmado", str(ctx.exception).lower())

    @patch("app.services.plantoes.get_connection")
    def test_dod3_checkin_allowed_when_confirmed(self, mock_get_conn):
        """Check-in bem-sucedido quando status é 'confirmado'."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        confirmed_plantao = {"id": 77, "profissional_id": 30, "status": "confirmado"}
        in_progress_plantao = dict(confirmed_plantao, status="em_andamento")
        mock_cursor.fetchone.side_effect = [confirmed_plantao, in_progress_plantao]

        res = realizar_checkin(plantao_id=77, profissional_id=30)
        self.assertEqual(res["status"], "em_andamento")

    @patch("app.services.plantoes.get_connection")
    def test_checkout_liberates_repasse(self, mock_get_conn):
        """Check-out pelo profissional transiciona para 'concluido' e libera repasse."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        in_progress = {"id": 88, "profissional_id": 30, "status": "em_andamento"}
        concluded = dict(in_progress, status="concluido")
        mock_cursor.fetchone.side_effect = [in_progress, concluded]

        res = realizar_checkout(plantao_id=88, profissional_id=30)
        self.assertEqual(res["status"], "concluido")

        # Verificar se executou UPDATE em repasses para 'liberado'
        executed_sqls = [c[0][0] for c in mock_cursor.execute.call_args_list]
        self.assertTrue(any("SET status = 'liberado'" in sql for sql in executed_sqls))

    @patch("app.services.plantoes.get_connection")
    def test_dod4_evaluation_blocked_before_conclusion(self, mock_get_conn):
        """
        Critério DoD 4:
        Familiar só consegue avaliar o profissional após o plantão estar no estado 'concluido'.
        """
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Plantão ainda em andamento
        mock_cursor.fetchone.return_value = {
            "id": 99,
            "familiar_id": 5,
            "profissional_id": 30,
            "status": "em_andamento",
        }

        with self.assertRaises(BusinessRuleError) as ctx:
            avaliar_plantao(plantao_id=99, familiar_id=5, nota=5, comentario="Ótimo")
        self.assertIn("conclusão", str(ctx.exception).lower())

    @patch("app.services.plantoes.get_connection")
    def test_dod4_evaluation_allowed_when_concluded(self, mock_get_conn):
        """Avaliação permitida com recálculo de nota média quando concluído."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        concluded = {
            "id": 99,
            "familiar_id": 5,
            "profissional_id": 30,
            "status": "concluido",
        }
        mock_cursor.fetchone.side_effect = [
            concluded,               # plantao
            None,                    # checagem de avaliacao duplicada
            {"media": 4.8, "total": 5}, # stats
        ]
        mock_cursor.lastrowid = 1

        res = avaliar_plantao(
            plantao_id=99,
            familiar_id=5,
            nota=5,
            comentario="Excelente cuidador, muito atencioso!",
        )
        self.assertEqual(res["nota"], 5)
        self.assertEqual(res["nota_media_atualizada"], 4.8)
        self.assertEqual(res["total_avaliacoes"], 5)


if __name__ == "__main__":
    unittest.main()

