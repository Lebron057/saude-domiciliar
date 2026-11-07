"""
Módulo de conexão e verificação passiva do MariaDB — Auth Service.
A gestão e aplicação de DDL/schema é delegada exclusivamente ao runner:
    python -m db.migrate
"""

import os
import mysql.connector
from mysql.connector import Error


def get_connection():
    """Cria e retorna uma conexão com o MariaDB usando variáveis de ambiente."""
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "saude_domiciliar"),
    )


def init_db():
    """
    Verificação passiva de prontidão do banco de dados na inicialização do serviço.
    Não executa comandos DDL imperativos (CREATE/ALTER TABLE).
    """
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SHOW TABLES LIKE 'schema_migrations'")
        has_migrations_table = cursor.fetchone() is not None

        if has_migrations_table:
            cursor.execute("SELECT versao FROM schema_migrations ORDER BY versao DESC LIMIT 1")
            row = cursor.fetchone()
            ultima_versao = row["versao"] if row else "nenhuma"
            print(f"[AuthService] Conexão com MariaDB estabelecida. Última migration aplicada: {ultima_versao}")
        else:
            print("[AuthService] AVISO: Tabela 'schema_migrations' não encontrada. Execute: python -m db.migrate")

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"[AuthService] Aviso ao verificar banco de dados na inicialização: {e}")
