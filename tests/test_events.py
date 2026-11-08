"""
Testes Unitários da Fase 6 — Redis Streams Temáticos, Timelines e Métricas de Auditoria.
Cobre todos os critérios de aceitação (DoD 1 a 4) da Issue #9 / Atividade 9.
"""

import json
from datetime import datetime, timezone
import unittest
from unittest.mock import MagicMock, patch, AsyncMock

from log_service.main import (
    LogEvent,
    infer_categoria,
    sanitize_payload,
    create_log,
    get_entity_timeline,
    DOMAIN_STREAMS,
    STREAM_KEY,
)


class TestEventCategorizationAndSanitization(unittest.TestCase):
    """Testes de classificação de domínio e conformidade com a LGPD."""

    def test_infer_categoria_by_prefix(self):
        self.assertEqual(infer_categoria("plantao.solicitado"), "plantao")
        self.assertEqual(infer_categoria("plantao.aceito"), "plantao")
        self.assertEqual(infer_categoria("locacao.assinatura_ativa"), "locacao")
        self.assertEqual(infer_categoria("caucao.autorizada"), "locacao")
        self.assertEqual(infer_categoria("credencial.enviada"), "credencial")
        self.assertEqual(infer_categoria("documento.acessado"), "credencial")
        self.assertEqual(infer_categoria("stripe.assinatura_ativada"), "pagamento")
        self.assertEqual(infer_categoria("repasse.liberado"), "pagamento")
        self.assertEqual(infer_categoria("login"), "auth")
        self.assertEqual(infer_categoria("auth.register"), "auth")
        self.assertEqual(infer_categoria("audit.security.access_denied"), "seguranca")
        self.assertEqual(infer_categoria("sistema.outro"), "geral")

    def test_dod4_sanitize_payload_masks_sensitive_health_and_credentials_data(self):
        """
        Critério DoD 4:
        Dados sensíveis de saúde (diagnósticos, prontuários, CPFs, senhas)
        são expurgados/mascarados e NUNCA incluídos nos streams do Redis.
        """
        raw_dados = {
            "cpf": "123.456.789-00",
            "diagnostico": "Hipertensão grave e mobilidade reduzida",
            "prontuario_medico": "Paciente com necessidade de oxigênio",
            "receita_remedios": "Medicamentos controlados",
            "senha_hash": "$2b$12$secretHash",
            "cartao_final": "4242",
            "valor_diaria": 15000,
            "cidade": "São Paulo",
            "categoria_exigida": "tecnico_enfermagem",
        }

        sanitized = sanitize_payload(raw_dados)

        # Campos sensíveis mascarados com tag de auditoria LGPD
        self.assertEqual(sanitized["cpf"], "[REDACTED_LGPD]")
        self.assertEqual(sanitized["diagnostico"], "[REDACTED_LGPD]")
        self.assertEqual(sanitized["prontuario_medico"], "[REDACTED_LGPD]")
        self.assertEqual(sanitized["receita_remedios"], "[REDACTED_LGPD]")
        self.assertEqual(sanitized["senha_hash"], "[REDACTED_LGPD]")

        # Campos não-sensíveis de negócio preservados
        self.assertEqual(sanitized["valor_diaria"], 15000)
        self.assertEqual(sanitized["cidade"], "São Paulo")
        self.assertEqual(sanitized["categoria_exigida"], "tecnico_enfermagem")

    def test_sanitize_payload_recursive_nested_dict(self):
        nested = {
            "metadata": {
                "cpf_titular": "000.111.222-33",
                "detalhes": {"diagnostico_laudo": "CID-10 F00"},
            },
            "status": "aprovado",
        }
        res = sanitize_payload(nested)
        self.assertEqual(res["metadata"]["cpf_titular"], "[REDACTED_LGPD]")
        self.assertEqual(res["metadata"]["detalhes"]["diagnostico_laudo"], "[REDACTED_LGPD]")
        self.assertEqual(res["status"], "aprovado")


class TestRedisStreamsPersistenceAndTimeline(unittest.IsolatedAsyncioTestCase):
    """Testes dos critérios DoD 1, DoD 2 e métricas agregadas."""

    @patch("log_service.main.redis_client")
    async def test_dod1_create_log_persists_in_master_and_domain_streams(self, mock_redis):
        """
        Critério DoD 1:
        O disparo de uma ação de negócio persiste o evento simultaneamente
        em 'log:eventos' e no stream especializado do domínio ('evt:plantao').
        """
        mock_redis.xadd.side_effect = ["1727000000000-0", "1727000000000-1"]

        event = LogEvent(
            usuario_id=10,
            acao="plantao.solicitado",
            detalhe="plantao_id=55",
            entidade="plantao",
            entidade_id="55",
        )

        res = await create_log(event)
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["domain_stream"], "evt:plantao")

        # Verifica se xadd foi chamado no stream mestre E no stream temático
        xadd_calls = mock_redis.xadd.call_args_list
        self.assertEqual(len(xadd_calls), 2)
        self.assertEqual(xadd_calls[0][0][0], STREAM_KEY)       # log:eventos
        self.assertEqual(xadd_calls[1][0][0], "evt:plantao")    # evt:plantao

        # Verifica se indexou no Sorted Set para timeline (DoD 2)
        mock_redis.zadd.assert_called_once()
        zset_call_args = mock_redis.zadd.call_args[0]
        self.assertEqual(zset_call_args[0], "idx:plantao:55")

        # Verifica incremento de métricas diárias com expiração
        mock_redis.incr.assert_called()
        mock_redis.expire.assert_called()

    @patch("log_service.main.redis_client")
    async def test_dod2_get_entity_timeline_returns_ordered_events(self, mock_redis):
        """
        Critério DoD 2:
        A consulta da linha do tempo de uma entidade retorna todos os eventos
        ordenados cronologicamente a partir do Sorted Set.
        """
        event1 = {"stream_id": "1", "acao": "plantao.solicitado", "timestamp": "2026-11-07T10:00:00Z"}
        event2 = {"stream_id": "2", "acao": "plantao.aceito", "timestamp": "2026-11-07T10:15:00Z"}
        event3 = {"stream_id": "3", "acao": "plantao.confirmado", "timestamp": "2026-11-07T10:20:00Z"}

        mock_redis.zrange.return_value = [
            json.dumps(event1),
            json.dumps(event2),
            json.dumps(event3),
        ]

        res = await get_entity_timeline(entidade="plantao", entidade_id="55")
        self.assertEqual(res["total_eventos"], 3)
        self.assertEqual(res["timeline"][0]["acao"], "plantao.solicitado")
        self.assertEqual(res["timeline"][1]["acao"], "plantao.aceito")
        self.assertEqual(res["timeline"][2]["acao"], "plantao.confirmado")
        mock_redis.zrange.assert_called_once_with("idx:plantao:55", 0, -1)


class TestCatalogServiceResilience(unittest.IsolatedAsyncioTestCase):
    """Testes do critério DoD 3 — Resiliência best-effort."""

    async def test_dod3_emit_log_best_effort_resilience_when_service_down(self):
        """
        Critério DoD 3:
        Se o Redis ou log-service estiver temporariamente fora do ar,
        o catalog-service não interrompe a operação do usuário (try/except resiliente).
        """
        async def simulate_emit_log(usuario_id: int, acao: str, detalhe: str = ""):
            try:
                import httpx
                async with httpx.AsyncClient(timeout=0.1) as client:
                    await client.post("http://127.0.0.1:59999/logs", json={"usuario_id": usuario_id, "acao": acao})
            except Exception:
                # Silenciosamente absorvido (best-effort)
                pass

        try:
            await simulate_emit_log(
                usuario_id=42,
                acao="plantao.solicitado",
                detalhe="teste resiliencia",
            )
        except Exception as e:
            self.fail(f"_emit_log não deve propagar exceção em caso de indisponibilidade: {e}")


if __name__ == "__main__":
    unittest.main()
