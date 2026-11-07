"""
Script de Seed para Produtos, Preços Recorrentes e Cauções no Stripe (Modo de Teste) — CuidaHome.
Uso:
    python scripts/stripe_seed_prices.py [--dry-run]

Responsabilidades:
  - Cria produtos e preços mensais recorrentes no Stripe utilizando lookup_keys únicas.
  - Sincroniza os IDs (stripe_product_id, stripe_price_id) na tabela 'equipamentos' no MariaDB.
  - Garante unidades físicas de estoque disponíveis na tabela 'unidades_equipamento'.
  - Idempotente: pode ser executado repetidamente sem duplicar produtos nem alterar preços existentes.
"""

import os
import sys

# Garante inclusão da raiz do projeto no PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def load_env_file(filepath: str = ".env"):
    """Carrega variáveis de ambiente do .env para execução local."""
    if not os.path.exists(filepath):
        return
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k not in os.environ:
                        os.environ[k] = v
    except Exception as e:
        print(f"[StripeSeed] Aviso ao carregar .env: {e}")


load_env_file()

try:
    import stripe
except ImportError:
    stripe = None

from app.database import get_connection

SEED_EQUIPAMENTOS = [
    {
        "slug_categoria": "cadeiras-de-rodas",
        "nome": "Cadeira de Rodas Manual Padrão",
        "descricao": "Cadeira de rodas dobrável em aço carbono, com apoio de pés removível e freios bilaterais.",
        "preco_mensal_centavos": 14900,   # R$ 149,00 / mês
        "valor_caucao_centavos": 60000,    # R$ 600,00 de garantia / hold
        "lookup_key": "cadeira_rodas_padrao_mensal",
        "patrimonios": ["CR-001", "CR-002", "CR-003"],
    },
    {
        "slug_categoria": "camas-hospitalares",
        "nome": "Cama Hospitalar Articulada (2 Movimentos)",
        "descricao": "Cama com cabeceira e peseira ajustáveis por manivelas, grades laterais e colchão impermeável.",
        "preco_mensal_centavos": 29000,   # R$ 290,00 / mês
        "valor_caucao_centavos": 150000,  # R$ 1.500,00 de garantia / hold
        "lookup_key": "cama_hospitalar_articulada_mensal",
        "patrimonios": ["CH-001", "CH-002"],
    },
    {
        "slug_categoria": "andadores-e-muletas",
        "nome": "Andador Fixo e Articulado em Alumínio",
        "descricao": "Andador em alumínio anodizado ultraleve com regulagem de altura e pontas de borracha aderentes.",
        "preco_mensal_centavos": 6900,    # R$ 69,00 / mês
        "valor_caucao_centavos": 25000,   # R$ 250,00 de garantia / hold
        "lookup_key": "andador_articulado_mensal",
        "patrimonios": ["AND-001", "AND-002", "AND-003"],
    },
    {
        "slug_categoria": "andadores-e-muletas",
        "nome": "Par de Muletas Axilares Reguláveis",
        "descricao": "Par de muletas com almofadas axilares macias e pino de regulagem dupla para estabilidade.",
        "preco_mensal_centavos": 3900,    # R$ 39,00 / mês
        "valor_caucao_centavos": 12000,   # R$ 120,00 de garantia / hold
        "lookup_key": "muletas_par_mensal",
        "patrimonios": ["MUL-001", "MUL-002"],
    },
]


def seed_stripe_and_db(dry_run: bool = False):
    stripe_key = os.getenv("STRIPE_API_KEY", "")
    is_stripe_active = bool(stripe and stripe_key and not stripe_key.startswith("sk_test_placeholder"))

    if is_stripe_active:
        stripe.api_key = stripe_key
        print(f"[StripeSeed] Conectado ao Stripe com chave {stripe_key[:12]}...")
    else:
        print("[StripeSeed] AVISO: Stripe em modo simulação (sem chave real de API). Gerando IDs fictícios consistentes.")

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Obter fornecedor para vincular os equipamentos (primeiro admin ou fornecedor existente)
        cursor.execute("SELECT id FROM usuarios WHERE role IN ('fornecedor_equipamento', 'admin') ORDER BY id ASC LIMIT 1")
        fornecedor = cursor.fetchone()
        fornecedor_id = fornecedor["id"] if fornecedor else 1

        for item in SEED_EQUIPAMENTOS:
            lookup = item["lookup_key"]
            print(f"\n[StripeSeed] Processando: {item['nome']} (lookup_key={lookup})")

            # 1. Stripe Product & Price
            stripe_prod_id = f"prod_mock_{lookup}"
            stripe_price_id = f"price_mock_{lookup}"

            if is_stripe_active and not dry_run:
                try:
                    # Busca preço por lookup_key
                    prices = stripe.Price.list(lookup_keys=[lookup], expand=["data.product"])
                    if prices.data:
                        price = prices.data[0]
                        stripe_price_id = price.id
                        stripe_prod_id = price.product.id if hasattr(price.product, "id") else price.product
                        print(f"  -> Preço já existente no Stripe: {stripe_price_id}")
                    else:
                        # Cria produto
                        prod = stripe.Product.create(
                            name=item["nome"],
                            description=item["descricao"],
                            metadata={"lookup_key": lookup, "categoria": item["slug_categoria"]},
                        )
                        stripe_prod_id = prod.id

                        # Cria preço mensal recorrente
                        price = stripe.Price.create(
                            product=stripe_prod_id,
                            unit_amount=item["preco_mensal_centavos"],
                            currency="brl",
                            recurring={"interval": "month"},
                            lookup_key=lookup,
                        )
                        stripe_price_id = price.id
                        print(f"  -> Criado no Stripe: prod={stripe_prod_id}, price={stripe_price_id}")
                except Exception as e:
                    print(f"  -> Erro ao criar no Stripe: {e}. Usando mock.")

            # 2. MariaDB: Atualizar ou Inserir equipamento
            cursor.execute("SELECT id FROM categorias_equipamento WHERE slug = %s", (item["slug_categoria"],))
            cat = cursor.fetchone()
            categoria_id = cat["id"] if cat else 1

            cursor.execute("SELECT id FROM equipamentos WHERE nome = %s", (item["nome"],))
            existing_eq = cursor.fetchone()

            if existing_eq:
                eq_id = existing_eq["id"]
                if not dry_run:
                    cursor.execute(
                        """
                        UPDATE equipamentos
                        SET preco_mensal_centavos = %s,
                            valor_caucao_centavos = %s,
                            stripe_product_id = %s,
                            stripe_price_id = %s,
                            ativo = TRUE
                        WHERE id = %s
                        """,
                        (item["preco_mensal_centavos"], item["valor_caucao_centavos"], stripe_prod_id, stripe_price_id, eq_id),
                    )
                print(f"  -> Equipamento id={eq_id} atualizado no banco relacional.")
            else:
                if not dry_run:
                    cursor.execute(
                        """
                        INSERT INTO equipamentos (
                            fornecedor_id, categoria_id, nome, descricao,
                            preco_mensal_centavos, valor_caucao_centavos,
                            stripe_product_id, stripe_price_id, ativo
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE)
                        """,
                        (
                            fornecedor_id, categoria_id, item["nome"], item["descricao"],
                            item["preco_mensal_centavos"], item["valor_caucao_centavos"],
                            stripe_prod_id, stripe_price_id,
                        ),
                    )
                    eq_id = cursor.lastrowid
                else:
                    eq_id = 999
                print(f"  -> Equipamento id={eq_id} inserido no banco relacional.")

            # 3. MariaDB: Inserir Unidades Físicas de Estoque
            if not dry_run:
                for pat in item["patrimonios"]:
                    cursor.execute(
                        """
                        INSERT IGNORE INTO unidades_equipamento (equipamento_id, numero_patrimonio, status)
                        VALUES (%s, %s, 'disponivel')
                        """,
                        (eq_id, pat),
                    )
                print(f"  -> Unidades físicas de estoque verificadas/garantidas: {', '.join(item['patrimonios'])}")

        if not dry_run:
            conn.commit()
            print("\n[StripeSeed] Sucesso: catálogo de equipamentos e preços sincronizados com MariaDB e Stripe.")
        else:
            print("\n[StripeSeed] Simulação (--dry-run) finalizada sem persistir alterações.")

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    is_dry = "--dry-run" in sys.argv
    seed_stripe_and_db(dry_run=is_dry)
