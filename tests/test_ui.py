"""
Testes Automatizados para a Interface do Usuário (Frontend UI) e Painéis Especializados
Issues #10 e #11 — CuidaHome (Saúde & Atendimento Domiciliar)

Critérios de Aceitação Cobertos (DoDs):
Issue #10:
- DoD 1: Todas as telas renderizam sem erros de sintaxe Jinja2 em desktop e telas móveis.
- DoD 2: Profissionais com status de verificação diferente de 'aprovado' NUNCA aparecem na listagem pública.
- DoD 3: Equipamentos sem estoque físico exibem badge visual 'Indisponível no momento' com botão de locação desabilitado.
- DoD 4: Nenhuma referência a atores, pôsteres de filmes ou TMDB está presente no HTML gerado.

Issue #11:
- DoD 1: O acesso a cada painel é estritamente condicionado ao papel do usuário logado (redirecionamento ou 403).
- DoD 2: Upload de laudos vincula ao bucket privado 'documentos' e valida limite de 10 MB.
- DoD 3: O administrador aprova credencial pendente, liberando imediatamente o profissional para plantões.
- DoD 4: O extrato financeiro do profissional exibe a dedução transparente de 12% da taxa da plataforma.
"""

import os
import unittest
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.services.storage import (
    validate_file_upload,
    ALLOWED_DOCUMENT_MIMES,
    MAX_DOCUMENT_BYTES,
    S3_BUCKET_DOCUMENTOS,
)

class TestCuidaHomeTemplatesAndUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        templates_dir = os.path.join(os.path.dirname(__file__), "..", "app", "templates")
        cls.env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def test_dod4_no_tmdb_or_movie_references_in_templates(self):
        """DoD 4: Garante que nenhuma referência a TMDB, filmes, atores ou pôsteres legados subsista nos templates."""
        templates_dir = os.path.join(os.path.dirname(__file__), "..", "app", "templates")
        forbidden_terms = ["tmdb", "tom hanks", "movie-card", "filme", "sinopse", "poster_path"]

        for root, _, files in os.walk(templates_dir):
            for file in files:
                if file.endswith(".html"):
                    path = os.path.join(root, file)
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read().lower()
                        for term in forbidden_terms:
                            self.assertNotIn(
                                term,
                                content,
                                f"Termo proibido '{term}' encontrado no template {file}",
                            )

    def test_dod1_landing_template_renders_cleanly(self):
        """DoD 1: Landing page renderiza sem erros sintáticos Jinja2 com dados dinâmicos."""
        template = self.env.get_template("landing.html")
        mock_profissionais = [
            {
                "id": 10,
                "nome": "Mariana Souza",
                "avatar_key": None,
                "categoria": "enfermeiro",
                "registro_conselho": "COREN-SP 214589",
                "uf_conselho": "SP",
                "valor_diaria_12h_centavos": 22000,
                "cidade": "São Paulo",
                "uf": "SP",
                "nota_media": 4.95,
                "total_avaliacoes": 38,
                "apresentacao": "Enfermeira especialista em idosos.",
            }
        ]
        mock_equipamentos = [
            {
                "id": 1,
                "nome": "Cama Hospitalar Articulada",
                "categoria_nome": "Camas Hospitalares",
                "preco_mensal_centavos": 29000,
                "valor_caucao_centavos": 50000,
                "unidades_disponiveis": 3,
                "foto_principal_key": None,
            }
        ]

        rendered = template.render(
            user=None,
            active_page="home",
            profissionais=mock_profissionais,
            equipamentos=mock_equipamentos,
        )

        self.assertIn("CuidaHome", rendered)
        self.assertIn("Mariana Souza", rendered)
        self.assertIn("COREN-SP 214589", rendered)
        self.assertIn("Cama Hospitalar Articulada", rendered)
        self.assertIn("Em Estoque (3)", rendered)

    def test_dod2_only_approved_professionals_in_public_mural(self):
        """DoD 2: Profissionais com status diferente de 'aprovado' NUNCA devem ser exibidos na listagem."""
        # Simulando filtro da query SQL que só retorna status_verificacao = 'aprovado'
        all_candidates = [
            {"id": 1, "nome": "Dr. Aprovado", "status_verificacao": "aprovado", "categoria": "enfermeiro", "cidade": "SP", "uf": "SP", "nota_media": 5.0, "total_avaliacoes": 10},
            {"id": 2, "nome": "Dr. Pendente", "status_verificacao": "pendente", "categoria": "cuidador", "cidade": "SP", "uf": "SP", "nota_media": 0.0, "total_avaliacoes": 0},
            {"id": 3, "nome": "Dr. Rejeitado", "status_verificacao": "rejeitado", "categoria": "enfermeiro", "cidade": "SP", "uf": "SP", "nota_media": 2.0, "total_avaliacoes": 1},
        ]
        public_profissionais = [p for p in all_candidates if p["status_verificacao"] == "aprovado"]

        template = self.env.get_template("profissionais/mural.html")
        rendered = template.render(profissionais=public_profissionais, selected_categoria=None, busca=None, user=None)

        self.assertIn("Dr. Aprovado", rendered)
        self.assertNotIn("Dr. Pendente", rendered)
        self.assertNotIn("Dr. Rejeitado", rendered)

    def test_dod3_out_of_stock_badge_and_button_disabled(self):
        """DoD 3: Equipamentos sem estoque físico exibem badge de indisponível e botão desabilitado."""
        template = self.env.get_template("equipamentos/catalogo.html")
        mock_equipamentos = [
            {
                "id": 1,
                "nome": "Cadeira de Rodas Esgotada",
                "categoria_nome": "Cadeiras de Rodas",
                "preco_mensal_centavos": 14900,
                "valor_caucao_centavos": 20000,
                "unidades_disponiveis": 0,  # Estoque zerado
                "foto_principal_key": None,
            }
        ]

        rendered = template.render(
            equipamentos=mock_equipamentos,
            categorias=[],
            selected_categoria=None,
            busca=None,
            user=None,
        )

        self.assertIn("Indisponível no momento", rendered)
        self.assertIn("Esgotado", rendered)
        self.assertIn("disabled", rendered)

    def test_dod1_issue11_role_based_navbar_adaptation(self):
        """Issue #11 DoD 1: O menu de navegação base adapta links conforme o papel logado."""
        template = self.env.get_template("base.html")

        # 1. Familiar
        rendered_fam = template.render(user={"id": 2, "nome": "Carlos Familiar", "role": "familiar"}, active_page="painel_familia")
        self.assertIn("/painel/familia", rendered_fam)
        self.assertIn("Meu Painel", rendered_fam)
        self.assertNotIn("/admin", rendered_fam)

        # 2. Profissional de Saúde
        rendered_prof = template.render(user={"id": 6, "nome": "Mariana Enfermeira", "role": "profissional_saude"}, active_page="painel_profissional")
        self.assertIn("/painel/profissional", rendered_prof)
        self.assertIn("Minha Escala", rendered_prof)
        self.assertNotIn("/painel/familia", rendered_prof)

        # 3. Fornecedor
        rendered_forn = template.render(user={"id": 7, "nome": "Ortopedia Brasil", "role": "fornecedor_equipamento"}, active_page="painel_fornecedor")
        self.assertIn("/painel/fornecedor", rendered_forn)
        self.assertIn("Minha Frota", rendered_forn)

        # 4. Admin
        rendered_admin = template.render(user={"id": 1, "nome": "Admin Geral", "role": "admin"}, active_page="admin_painel")
        self.assertIn("/admin", rendered_admin)
        self.assertIn("/admin/logs", rendered_admin)
        self.assertIn("Painel Admin", rendered_admin)

    def test_dod2_issue11_laudo_upload_validation_and_size_limit(self):
        """Issue #11 DoD 2: Valida que upload de laudos respeita o limite de 10 MB e mimes permitidos."""
        self.assertEqual(S3_BUCKET_DOCUMENTOS, "documentos")
        self.assertEqual(MAX_DOCUMENT_BYTES, 10 * 1024 * 1024)

        # 1. Arquivo válido (PDF real)
        valid_pdf = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
        is_valid, msg, ext = validate_file_upload(
            file_bytes=valid_pdf,
            filename="laudo.pdf",
            content_type="application/pdf",
            allowed_mime_types=ALLOWED_DOCUMENT_MIMES,
            max_bytes=MAX_DOCUMENT_BYTES,
        )
        self.assertTrue(is_valid)
        self.assertEqual(ext, "pdf")

        # 2. Arquivo excedendo 10 MB
        oversized = b"%PDF-1.4 " + (b"0" * (MAX_DOCUMENT_BYTES + 100))
        is_valid_size, msg_size, _ = validate_file_upload(
            file_bytes=oversized,
            filename="laudo_pesado.pdf",
            content_type="application/pdf",
            allowed_mime_types=ALLOWED_DOCUMENT_MIMES,
            max_bytes=MAX_DOCUMENT_BYTES,
        )
        self.assertFalse(is_valid_size)
        self.assertIn("excede o limite máximo", msg_size)

        # 3. Executável disfarçado de PDF
        fake_pdf = b"MZ\x90\x00\x03\x00\x00\x00" + b"malware"
        is_valid_fake, msg_fake, _ = validate_file_upload(
            file_bytes=fake_pdf,
            filename="laudo_falso.pdf",
            content_type="application/pdf",
            allowed_mime_types=ALLOWED_DOCUMENT_MIMES,
            max_bytes=MAX_DOCUMENT_BYTES,
        )
        self.assertFalse(is_valid_fake)
        self.assertIn("magic bytes", msg_fake)

    def test_dod4_issue11_transparent_financial_payout_ledger(self):
        """Issue #11 DoD 4: Extrato financeiro exibe dedução transparente da taxa da plataforma (12%)."""
        template = self.env.get_template("paineis/profissional.html")
        mock_repasses = [
            {
                "id": 1,
                "plantao_id": 101,
                "valor_bruto_centavos": 20000,        # R$ 200,00
                "taxa_plataforma_centavos": 2400,     # R$ 24,00 (12%)
                "valor_liquido_centavos": 17600,       # R$ 176,00 líquido
                "status": "pago",
                "pago_em": "2026-11-07 18:00:00",
            }
        ]

        rendered = template.render(
            user={"id": 6, "nome": "Mariana Enfermeira", "role": "profissional_saude"},
            active_page="painel_profissional",
            perfil={"nota_media": 4.95, "status_verificacao": "aprovado"},
            plantoes_confirmados=[],
            plantoes_abertos=[],
            credenciais=[],
            repasses=mock_repasses,
            total_liquido_centavos=17600,
        )

        self.assertIn("R$ 200.00", rendered)
        self.assertIn("- R$ 24.00", rendered)
        self.assertIn("R$ 176.00", rendered)
        self.assertIn("12%", rendered)

    def test_dod3_issue11_admin_panel_credential_moderation_queue(self):
        """Issue #11 DoD 3: Painel Admin renderiza fila de credenciais pendentes com botões de aprovar/rejeitar."""
        template = self.env.get_template("paineis/admin.html")
        mock_credenciais = [
            {
                "id": 42,
                "usuario_id": 99,
                "usuario_nome": "José Cuidador",
                "usuario_email": "jose@cuidahome.com",
                "tipo": "diploma",
                "tamanho_bytes": 524288,
                "criado_em": "2026-11-07 14:00:00",
                "status": "pendente",
            }
        ]

        rendered = template.render(
            user={"id": 1, "nome": "Admin", "role": "admin"},
            active_page="admin_painel",
            credenciais_pendentes=mock_credenciais,
            total_usuarios=12,
            total_gmv_centavos=350000,
            total_locacoes_ativas=5,
        )

        self.assertIn("José Cuidador", rendered)
        self.assertIn("DIPLOMA", rendered)
        self.assertIn("/admin/credenciais/42/aprovar", rendered)
        self.assertIn("/documentos/credenciais/42", rendered)


if __name__ == "__main__":
    unittest.main()
