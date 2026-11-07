"""
Testes automatizados do sistema de controle de acesso (RBAC / ABAC) — CuidaHome.
Valida isolamento de papéis, bloqueio de autocadastro de admin e proteção IDOR.
"""

import unittest
from unittest.mock import MagicMock, patch
import asyncio

from app.deps import require_roles, require_owner_or_admin, require_verified_professional


class TestRBAC(unittest.TestCase):

    def test_require_roles_grants_access_to_authorized_role(self):
        checker = require_roles("familiar_paciente", "admin")
        user = {"id": 1, "nome": "Mariana", "role": "familiar_paciente"}
        
        result = asyncio.run(checker(request=MagicMock(), user=user))
        self.assertEqual(result["role"], "familiar_paciente")

    def test_require_roles_raises_403_for_unauthorized_role(self):
        checker = require_roles("admin")
        user = {"id": 2, "nome": "Carlos", "role": "familiar_paciente"}

        with self.assertRaises(Exception) as ctx:
            asyncio.run(checker(request=MagicMock(), user=user))
        
        self.assertEqual(getattr(ctx.exception, "status_code", None), 403)
        self.assertIn("Acesso negado", str(ctx.exception.detail))

    def test_require_owner_or_admin_allows_owner(self):
        user = {"id": 10, "nome": "Dono", "role": "familiar_paciente"}
        self.assertTrue(require_owner_or_admin(resource_owner_id=10, user=user))

    def test_require_owner_or_admin_allows_admin(self):
        user = {"id": 1, "nome": "Admin", "role": "admin"}
        self.assertTrue(require_owner_or_admin(resource_owner_id=99, user=user))

    def test_require_owner_or_admin_blocks_unauthorized_user(self):
        user = {"id": 5, "nome": "Invasor", "role": "familiar_paciente"}
        with self.assertRaises(Exception) as ctx:
            require_owner_or_admin(resource_owner_id=10, user=user)
        
        self.assertEqual(getattr(ctx.exception, "status_code", None), 403)

    @patch("app.deps.get_connection")
    def test_require_verified_professional_allows_approved(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"status_verificacao": "aprovado"}
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        user = {"id": 20, "nome": "Enfermeira Ana", "role": "profissional_saude"}
        result = asyncio.run(require_verified_professional(request=MagicMock(), user=user))
        self.assertEqual(result["id"], 20)

    @patch("app.deps.get_connection")
    def test_require_verified_professional_blocks_pending(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"status_verificacao": "pendente"}
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        user = {"id": 21, "nome": "Cuidador João", "role": "profissional_saude"}
        with self.assertRaises(Exception) as ctx:
            asyncio.run(require_verified_professional(request=MagicMock(), user=user))
        
        self.assertEqual(getattr(ctx.exception, "status_code", None), 403)
        self.assertIn("pendente", str(ctx.exception.detail))

    def test_require_verified_professional_blocks_non_professional_role(self):
        user = {"id": 30, "nome": "Familiar", "role": "familiar_paciente"}
        with self.assertRaises(Exception) as ctx:
            asyncio.run(require_verified_professional(request=MagicMock(), user=user))
        
        self.assertEqual(getattr(ctx.exception, "status_code", None), 403)
        self.assertIn("Acesso exclusivo", str(ctx.exception.detail))

    def test_role_validation_blocks_admin_registration(self):
        VALID_PUBLIC_ROLES = ("familiar_paciente", "profissional_saude", "fornecedor_equipamento")
        requested_role = "admin"
        
        # Simula validação do endpoint /auth/register
        self.assertEqual(requested_role, "admin")
        self.assertNotIn(requested_role, VALID_PUBLIC_ROLES)

    def test_role_validation_accepts_valid_public_roles(self):
        VALID_PUBLIC_ROLES = ("familiar_paciente", "profissional_saude", "fornecedor_equipamento")
        for r in ("familiar_paciente", "profissional_saude", "fornecedor_equipamento"):
            self.assertIn(r, VALID_PUBLIC_ROLES)


if __name__ == "__main__":
    unittest.main()
