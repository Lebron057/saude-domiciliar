"""
Script para popular dados de demonstração da CuidaHome na MariaDB.
Cria perfis de profissionais de saúde verificados (status_verificacao = 'aprovado'),
equipamentos complementares com unidades físicas, pacientes de teste e credenciais.
"""

import os
import sys
from pathlib import Path

# Carrega .env se existir localmente
env_file = Path(".env")
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.database import get_connection

def seed_demo_data():
    conn = get_connection()
    try:
        with conn.cursor(dictionary=True) as cur:
            print("[Seed] Iniciando seed de dados demonstrativos do frontend...")

            # 1. Obter ou criar usuários profissionais de saúde
            profissionais_seed = [
                {
                    "nome": "Mariana Souza",
                    "email": "mariana.enfermeira@cuidahome.com.br",
                    "role": "profissional_saude",
                    "categoria": "enfermeiro",
                    "registro_conselho": "COREN-SP 214589",
                    "uf_conselho": "SP",
                    "valor_diaria_12h_centavos": 22000,
                    "valor_diaria_24h_centavos": 40000,
                    "cidade": "São Paulo",
                    "uf": "SP",
                    "apresentacao": "Enfermeira graduada pela USP com 8 anos de experiência em cuidados intensivos e atendimento domiciliar pós-cirúrgico.",
                    "nota_media": 4.95,
                    "total_avaliacoes": 38,
                },
                {
                    "nome": "Carlos Eduardo Mendes",
                    "email": "carlos.cuidador@cuidahome.com.br",
                    "role": "profissional_saude",
                    "categoria": "cuidador",
                    "registro_conselho": None,
                    "uf_conselho": "SP",
                    "valor_diaria_12h_centavos": 16000,
                    "valor_diaria_24h_centavos": 29000,
                    "cidade": "São Paulo",
                    "uf": "SP",
                    "apresentacao": "Cuidador certificado com especialização no manejo humanizado de Alzheimer e Parkinson. Pontual e atencioso.",
                    "nota_media": 5.00,
                    "total_avaliacoes": 29,
                },
                {
                    "nome": "Beatriz Oliveira",
                    "email": "beatriz.tec@cuidahome.com.br",
                    "role": "profissional_saude",
                    "categoria": "tecnico_enfermagem",
                    "registro_conselho": "COREN-SP 589123-TE",
                    "uf_conselho": "SP",
                    "valor_diaria_12h_centavos": 18000,
                    "valor_diaria_24h_centavos": 33000,
                    "cidade": "Campinas",
                    "uf": "SP",
                    "apresentacao": "Técnica de enfermagem com expertise em administração de medicamentos endovenosos, sondagens e curativos especiais.",
                    "nota_media": 4.90,
                    "total_avaliacoes": 42,
                },
                {
                    "nome": "Fernanda Ribeiro",
                    "email": "fernanda.cuidadora@cuidahome.com.br",
                    "role": "profissional_saude",
                    "categoria": "cuidador",
                    "registro_conselho": None,
                    "uf_conselho": "SP",
                    "valor_diaria_12h_centavos": 15000,
                    "valor_diaria_24h_centavos": 27000,
                    "cidade": "Santos",
                    "uf": "SP",
                    "apresentacao": "Cuidadora dedicada com 6 anos de experiência em cuidados paliativos, estímulo cognitivo e auxílio motor diário.",
                    "nota_media": 4.88,
                    "total_avaliacoes": 19,
                },
                {
                    "nome": "Roberto Silveira",
                    "email": "roberto.enfermeiro@cuidahome.com.br",
                    "role": "profissional_saude",
                    "categoria": "enfermeiro",
                    "registro_conselho": "COREN-SP 312908",
                    "uf_conselho": "SP",
                    "valor_diaria_12h_centavos": 24000,
                    "valor_diaria_24h_centavos": 45000,
                    "cidade": "São Paulo",
                    "uf": "SP",
                    "apresentacao": "Enfermeiro especialista em estomaterapia e reabilitação de lesões por pressão. Atendimento domiciliar humanizado de alta complexidade.",
                    "nota_media": 4.97,
                    "total_avaliacoes": 51,
                },
                {
                    "nome": "Luciana Martins",
                    "email": "luciana.cuidadora@cuidahome.com.br",
                    "role": "profissional_saude",
                    "categoria": "cuidador",
                    "registro_conselho": None,
                    "uf_conselho": "SP",
                    "valor_diaria_12h_centavos": 15500,
                    "valor_diaria_24h_centavos": 28000,
                    "cidade": "São Bernardo do Campo",
                    "uf": "SP",
                    "apresentacao": "Cuidadora experiente no acompanhamento hospitalar e domiciliar diurno e noturno. Empática, responsável e paciente.",
                    "nota_media": 4.92,
                    "total_avaliacoes": 33,
                },
            ]

            admin_id = 1
            for p in profissionais_seed:
                # Verificar se o usuário já existe
                cur.execute("SELECT id FROM usuarios WHERE email = %s", (p["email"],))
                u = cur.fetchone()
                if not u:
                    cur.execute(
                        """INSERT INTO usuarios (nome, email, senha_hash, role)
                           VALUES (%s, %s, %s, %s)""",
                        (p["nome"], p["email"], "scrypt:demo:hash", p["role"]),
                    )
                    user_id = cur.lastrowid
                else:
                    user_id = u["id"]

                # Inserir ou atualizar perfil profissional
                cur.execute(
                    """INSERT INTO perfis_profissionais (
                           usuario_id, categoria, registro_conselho, uf_conselho,
                           valor_diaria_12h_centavos, valor_diaria_24h_centavos,
                           cidade, uf, apresentacao, status_verificacao,
                           verificado_por, verificado_em, nota_media, total_avaliacoes
                       ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'aprovado', %s, NOW(), %s, %s)
                       ON DUPLICATE KEY UPDATE
                           categoria = VALUES(categoria),
                           registro_conselho = VALUES(registro_conselho),
                           valor_diaria_12h_centavos = VALUES(valor_diaria_12h_centavos),
                           valor_diaria_24h_centavos = VALUES(valor_diaria_24h_centavos),
                           apresentacao = VALUES(apresentacao),
                           status_verificacao = 'aprovado',
                           nota_media = VALUES(nota_media),
                           total_avaliacoes = VALUES(total_avaliacoes)""",
                    (
                        user_id,
                        p["categoria"],
                        p["registro_conselho"],
                        p["uf_conselho"],
                        p["valor_diaria_12h_centavos"],
                        p["valor_diaria_24h_centavos"],
                        p["cidade"],
                        p["uf"],
                        p["apresentacao"],
                        admin_id,
                        p["nota_media"],
                        p["total_avaliacoes"],
                    ),
                )

                # Inserir credencial aprovada se tiver registro
                if p["registro_conselho"]:
                    cur.execute(
                        """INSERT IGNORE INTO credenciais (usuario_id, tipo, object_key, mime, tamanho_bytes, status, revisado_por, revisado_em)
                           VALUES (%s, 'coren', %s, 'application/pdf', 1048576, 'aprovado', %s, NOW())""",
                        (user_id, f"demo_cred_{user_id}.pdf", admin_id),
                    )

            # 2. Equipamentos complementares
            cur.execute("SELECT id FROM categorias_equipamento WHERE slug = 'camas'")
            cat_cama = cur.fetchone()
            cama_cat_id = cat_cama["id"] if cat_cama else 1

            cur.execute("SELECT id FROM categorias_equipamento WHERE slug = 'outros'")
            cat_outros = cur.fetchone()
            outros_cat_id = cat_outros["id"] if cat_outros else 1

            equipamentos_adicionais = [
                {
                    "nome": "Poltrona Hospitalar Reclinável do Papai",
                    "categoria_id": outros_cat_id,
                    "descricao": "Poltrona reclinável em courvin hospitalar lavável, ideal para acompanhantes e idosos com repouso pós-operatório prolongado.",
                    "preco_mensal_centavos": 18000,
                    "valor_caucao_centavos": 25000,
                    "patrimonios": ["CH-POL-001", "CH-POL-002"],
                },
                {
                    "nome": "Concentrador de Oxigênio Domiciliar 5L",
                    "categoria_id": outros_cat_id,
                    "descricao": "Concentrador de oxigênio medicinal contínuo de 1 a 5 LPM, silencioso, com alarme de pureza e rodízios para fácil transporte.",
                    "preco_mensal_centavos": 35000,
                    "valor_caucao_centavos": 60000,
                    "patrimonios": ["CH-OXI-001", "CH-OXI-002"],
                },
            ]

            for eq in equipamentos_adicionais:
                cur.execute("SELECT id FROM equipamentos WHERE nome = %s", (eq["nome"],))
                e_row = cur.fetchone()
                if not e_row:
                    cur.execute(
                        """INSERT INTO equipamentos (fornecedor_id, categoria_id, nome, descricao, preco_mensal_centavos, valor_caucao_centavos, ativo)
                           VALUES (%s, %s, %s, %s, %s, %s, TRUE)""",
                        (admin_id, eq["categoria_id"], eq["nome"], eq["descricao"], eq["preco_mensal_centavos"], eq["valor_caucao_centavos"]),
                    )
                    eq_id = cur.lastrowid
                else:
                    eq_id = e_row["id"]

                for pat in eq["patrimonios"]:
                    cur.execute(
                        """INSERT IGNORE INTO unidades_equipamento (equipamento_id, numero_patrimonio, status)
                           VALUES (%s, %s, 'disponivel')""",
                        (eq_id, pat),
                    )

            # 3. Pacientes de teste vinculados ao usuário de teste familiar (id 2 ou id 4)
            cur.execute("SELECT id FROM usuarios WHERE role LIKE '%familiar%' LIMIT 1")
            fam = cur.fetchone()
            familiar_id = fam["id"] if fam else 2

            cur.execute("SELECT id FROM pacientes WHERE familiar_id = %s", (familiar_id,))
            pac = cur.fetchone()
            if not pac:
                cur.execute(
                    """INSERT INTO pacientes (familiar_id, nome, data_nascimento, cidade, uf, condicao_resumo, mobilidade, alergias_restricoes, contato_emergencia, ativo)
                       VALUES (%s, 'Dona Maria Helena Silva', '1948-05-14', 'São Paulo', 'SP', 'Recuperação de AVC isquêmico leve, necessita auxílio para higiene e medicamentos.', 'mobilidade_reduzida', 'Alergia a Dipirona e Sulfas', '(11) 98765-4321', TRUE)""",
                    (familiar_id,),
                )
                paciente_id = cur.lastrowid
                print(f"[Seed] Paciente criado com ID: {paciente_id}")

            conn.commit()
            print("[Seed] Seed de dados do frontend concluído com sucesso!")
    finally:
        conn.close()

if __name__ == "__main__":
    seed_demo_data()
