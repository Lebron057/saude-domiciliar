"""
Testes Unitários da Fase 5 — Locação de Equipamentos, Estoque, Assinaturas Stripe e Caução.
Cobre todos os critérios de aceitação (DoD 1 a 4) da Issue #8 / Atividade 9.
"""

from datetime import date, timedelta
import unittest
from unittest.mock import MagicMock, patch

from app.services.locacoes import (
    solicitar_locacao,
    confirmar_pagamento_locacao,
    renovar_locacao_mensal,
    marcar_locacao_inadimplente,
    solicitar_devolucao_locacao,
    realizar_vistoria_e_encerramento,
    verificar_disponibilidade_estoque,
    BusinessRuleError,
)


class TestLocacoesAndEstoque(unittest.TestCase):
    """Testes de regras de negócio, verificação de estoque e contratos."""

    @patch("app.services.locacoes.get_connection")
    def test_verificar_disponibilidade_estoque_com_unidades(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchall.return_value = [
            {"id": 1, "numero_patrimonio": "CR-001"},
            {"id": 2, "numero_patrimonio": "CR-002"},
        ]

        disp = verificar_disponibilidade_estoque(1)
        self.assertTrue(disp["disponivel"])
        self.assertEqual(disp["unidades_disponiveis"], 2)
        self.assertEqual(disp["proxima_unidade_id"], 1)

    @patch("app.services.locacoes.get_connection")
    def test_verificar_disponibilidade_estoque_vazio(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchall.return_value = []

        disp = verificar_disponibilidade_estoque(99)
        self.assertFalse(disp["disponivel"])
        self.assertEqual(disp["unidades_disponiveis"], 0)
        self.assertIsNone(disp["proxima_unidade_id"])

    @patch("app.services.locacoes.verificar_disponibilidade_estoque")
    def test_dod4_solicitar_locacao_rejeita_sem_estoque(self, mock_disp):
        """
        Critério DoD 4:
        Tentativa de locação em equipamento sem unidades físicas disponíveis no estoque
        retorna mensagem amigável de indisponibilidade.
        """
        mock_disp.return_value = {
            "disponivel": False,
            "unidades_disponiveis": 0,
            "proxima_unidade_id": None,
        }

        with self.assertRaises(BusinessRuleError) as ctx:
            solicitar_locacao(
                cliente_id=5,
                equipamento_id=2,
                endereco_entrega="Rua das Flores, 123",
                cidade="São Paulo",
                uf="SP",
                data_entrega_prevista=date.today() + timedelta(days=2),
                aceite_termo=True,
                client_ip="192.168.1.1",
            )
        self.assertIn("sem unidades disponíveis no estoque", str(ctx.exception).lower())

    def test_solicitar_locacao_rejeita_sem_aceite_termo(self):
        with self.assertRaises(BusinessRuleError) as ctx:
            solicitar_locacao(
                cliente_id=5,
                equipamento_id=2,
                endereco_entrega="Rua das Flores, 123",
                cidade="São Paulo",
                uf="SP",
                data_entrega_prevista=date.today() + timedelta(days=2),
                aceite_termo=False,  # Não aceitou o termo
                client_ip="192.168.1.1",
            )
        self.assertIn("aceite digital", str(ctx.exception).lower())

    @patch("app.services.locacoes.verificar_disponibilidade_estoque")
    @patch("app.services.locacoes.get_connection")
    def test_solicitar_locacao_sucesso_com_estoque(self, mock_get_conn, mock_disp):
        mock_disp.return_value = {
            "disponivel": True,
            "unidades_disponiveis": 1,
            "proxima_unidade_id": 10,
        }
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchone.side_effect = [
            {"id": 1, "nome": "Cadeira de Rodas", "ativo": True}, # eq
            {"id": 100, "status": "pendente_pagamento", "unidade_id": 10}, # locacao criada
        ]
        mock_cursor.lastrowid = 100

        locacao = solicitar_locacao(
            cliente_id=5,
            equipamento_id=1,
            endereco_entrega="Rua Teste, 456",
            cidade="Campinas",
            uf="SP",
            data_entrega_prevista=date.today() + timedelta(days=3),
            aceite_termo=True,
            client_ip="127.0.0.1",
        )
        self.assertEqual(locacao["status"], "pendente_pagamento")

        # Verifica reserva da unidade e inserção do contrato
        sqls = [c[0][0] for c in mock_cursor.execute.call_args_list]
        self.assertTrue(any("INSERT INTO contratos" in sql for sql in sqls))
        self.assertTrue(any("UPDATE unidades_equipamento SET status = 'locado'" in sql for sql in sqls))


class TestStripeBillingAndCaucao(unittest.TestCase):
    """Testes dos critérios de aceitação DoD 1, DoD 2 e DoD 3."""

    @patch("app.services.locacoes.get_connection")
    def test_dod1_confirmar_pagamento_transiciona_em_separacao_e_cria_caucao(self, mock_get_conn):
        """
        Critério DoD 1:
        Ao concluir o checkout de locação, a locação transiciona para 'em_separacao'
        e uma autorização de caução (hold/PaymentIntent) é gerada.
        """
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        loc_pendente = {
            "id": 40,
            "cliente_id": 12,
            "equipamento_id": 1,
            "status": "pendente_pagamento",
        }
        loc_em_separacao = dict(loc_pendente, status="em_separacao")

        mock_cursor.fetchone.side_effect = [
            loc_pendente,                                   # locacao inicial
            {"valor_caucao_centavos": 60000},               # equipamento
            loc_em_separacao,                               # locacao final
        ]

        locacao = confirmar_pagamento_locacao(
            locacao_id=40,
            stripe_subscription_id="sub_test_123",
            stripe_customer_id="cus_test_456",
            stripe_session_id="cs_test_789",
            mock_hold_intent_id="pi_hold_60000",
        )
        self.assertEqual(locacao["status"], "em_separacao")

        # Verificar se inseriu linha em caucoes com status 'autorizada'
        sqls = [c[0][0] for c in mock_cursor.execute.call_args_list]
        self.assertTrue(any("INSERT INTO caucoes" in sql for sql in sqls))

        caucao_call = [c for c in mock_cursor.execute.call_args_list if "INSERT INTO caucoes" in c[0][0]][0]
        params = caucao_call[0][1]
        self.assertEqual(params[0], 40)       # locacao_id
        self.assertEqual(params[1], 60000)    # valor_centavos
        self.assertEqual(params[2], "pi_hold_60000") # stripe_payment_intent_id

    @patch("app.services.locacoes.get_connection")
    def test_dod2_renovar_locacao_mensal_without_duplicating_lease(self, mock_get_conn):
        """
        Critério DoD 2:
        O webhook invoice.paid de renovação periódica registra o evento de renovação
        e cria o repasse mensal ao fornecedor sem duplicar locações.
        """
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        mock_cursor.fetchone.return_value = {
            "id": 40,
            "cliente_id": 12,
            "fornecedor_id": 2,
            "preco_mensal_centavos": 14900,
            "stripe_subscription_id": "sub_test_123",
        }

        locacao = renovar_locacao_mensal("sub_test_123")
        self.assertIsNotNone(locacao)
        self.assertEqual(locacao["id"], 40)

        # Verifica se gerou repasse da fatura de locação
        sqls = [c[0][0] for c in mock_cursor.execute.call_args_list]
        self.assertTrue(any("INSERT INTO repasses" in sql for sql in sqls))

        # Garantir que NÃO fez INSERT INTO locacoes (sem duplicação)
        self.assertFalse(any("INSERT INTO locacoes" in sql for sql in sqls))

    @patch("app.services.locacoes.get_connection")
    def test_dod3_vistoria_aprovada_libera_caucao_sem_cobrar_cliente(self, mock_get_conn):
        """
        Critério DoD 3:
        Solicitação de devolução com vistoria aprovada libera a autorização de caução
        sem debitar o valor do cliente e libera a unidade física para novas locações.
        """
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        loc_devolvida = {
            "id": 40,
            "unidade_id": 10,
            "status": "devolucao_solicitada",
        }
        loc_encerrada = dict(loc_devolvida, status="encerrada")

        mock_cursor.fetchone.side_effect = [loc_devolvida, loc_encerrada]

        res = realizar_vistoria_e_encerramento(
            locacao_id=40,
            responsavel_id=2,
            aprovado_sem_avarias=True,
            observacoes="Equipamento devolvido limpo e sem defeitos.",
        )
        self.assertEqual(res["status"], "encerrada")

        sqls = [c[0][0] for c in mock_cursor.execute.call_args_list]

        # Verificar se atualizou caução para 'liberada'
        self.assertTrue(any("UPDATE caucoes\n                SET status = 'liberada'" in sql for sql in sqls))

        # Verificar se liberou unidade física no estoque
        self.assertTrue(any("UPDATE unidades_equipamento SET status = 'disponivel'" in sql for sql in sqls))

    @patch("app.services.locacoes.get_connection")
    def test_vistoria_com_avaria_mantem_caucao_capturada_parcial(self, mock_get_conn):
        """Vistoria com avaria reportada retém caução para apuração de danos."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        loc = {"id": 40, "unidade_id": 10, "status": "devolucao_solicitada"}
        mock_cursor.fetchone.side_effect = [loc, loc]

        realizar_vistoria_e_encerramento(
            locacao_id=40,
            responsavel_id=2,
            aprovado_sem_avarias=False,
            observacoes="Apoio de braço quebrado pelo usuário.",
        )

        sqls = [c[0][0] for c in mock_cursor.execute.call_args_list]
        self.assertTrue(any("SET status = 'capturada_parcial'" in sql for sql in sqls))


if __name__ == "__main__":
    unittest.main()
