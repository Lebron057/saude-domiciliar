"""
Runner determinístico de migrations para MariaDB — CuidaHome.
Gerencia a aplicação sequencial e idempotente de scripts SQL versionados (V001..V010).

Uso:
    python -m db.migrate                 # Aplica todas as migrations pendentes (exceto contract)
    python -m db.migrate --status        # Exibe histórico e status das migrations
    python -m db.migrate --dry-run       # Simula a execução sem aplicar alterações
    python -m db.migrate --allow-contract # Habilita aplicação de migrations de contração (V010)
"""

import os
import sys
import time
import hashlib
import argparse
from pathlib import Path
import mysql.connector


MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def load_env_file(filepath: Path = Path(".env")):
    """Carrega variáveis do arquivo .env se existirem e não estiverem no ambiente."""
    if not filepath.exists():
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
        print(f"[Migrate] Aviso ao carregar .env: {e}")


def get_db_connection():
    """Retorna conexão ativa com o MariaDB."""
    load_env_file()
    host = os.getenv("DB_HOST", "localhost")
    port = int(os.getenv("DB_PORT", "3306"))
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD", "")
    database = os.getenv("DB_NAME", "saude_domiciliar")

    return mysql.connector.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        connection_timeout=15,
        autocommit=True,
    )


def calculate_checksum(content: str) -> str:
    """Calcula hash SHA-256 do conteúdo SQL normalizado."""
    normalized = content.replace("\r\n", "\n").strip().encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()


def split_sql_statements(sql_text: str) -> list[str]:
    """Divide script SQL em comandos individuais respeitando delimitadores ponto-e-vírgula."""
    statements = []
    current = []
    in_single_quote = False
    in_double_quote = False

    for line in sql_text.splitlines():
        trimmed = line.strip()
        # Ignora linhas de comentários inteiras
        if not in_single_quote and not in_double_quote and (trimmed.startswith("--") or trimmed.startswith("#")):
            continue
        current.append(line)
        if trimmed.endswith(";"):
            full_stmt = "\n".join(current).strip()
            if full_stmt:
                statements.append(full_stmt)
            current = []

    if current:
        remaining = "\n".join(current).strip()
        if remaining:
            statements.append(remaining)

    return statements


def ensure_migrations_table(conn):
    """Cria a tabela de metadados schema_migrations se não existir."""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            versao VARCHAR(20) PRIMARY KEY,
            descricao VARCHAR(255) NOT NULL,
            checksum CHAR(64) NOT NULL,
            aplicado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            duracao_ms INT NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """)
    cursor.close()


def get_applied_migrations(conn) -> dict[str, str]:
    """Retorna dicionário {versao: checksum} de migrations já registradas."""
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT versao, checksum FROM schema_migrations ORDER BY versao ASC")
    rows = cursor.fetchall()
    cursor.close()
    return {row["versao"]: row["checksum"] for row in rows}


def run_migrations(dry_run: bool = False, status_only: bool = False, allow_contract: bool = False):
    conn = get_db_connection()
    ensure_migrations_table(conn)

    # Bloqueio distribuído para evitar execuções concorrentes
    cursor = conn.cursor()
    cursor.execute("SELECT GET_LOCK('cuida_home_schema_migrations', 30)")
    lock_acquired = cursor.fetchone()[0] == 1
    cursor.close()

    if not lock_acquired:
        conn.close()
        raise SystemExit("[Migrate ERROR] Falha ao obter lock de migração no banco de dados (timeout 30s).")

    try:
        applied = get_applied_migrations(conn)
        all_files = sorted(MIGRATIONS_DIR.glob("V*.sql"))

        if not all_files:
            print("[Migrate] Nenhum arquivo de migração encontrado em db/migrations.")
            return

        print(f"==================================================")
        print(f"CuidaHome — Runner de Migrações MariaDB")
        print(f"Total de migrations no repositório: {len(all_files)}")
        print(f"Total de migrations já aplicadas:  {len(applied)}")
        print(f"==================================================")

        if status_only:
            print(f"{'VERSÃO':<10} | {'STATUS':<12} | {'ARQUIVO'}")
            print("-" * 60)
            for f in all_files:
                versao = f.name.split("__")[0]
                status_str = "APLICADA" if versao in applied else "PENDENTE"
                print(f"{versao:<10} | {status_str:<12} | {f.name}")
            return

        pending_count = 0
        for arq in all_files:
            nome_arquivo = arq.name
            versao = nome_arquivo.split("__")[0]
            descricao = nome_arquivo.split("__", 1)[1].replace(".sql", "") if "__" in nome_arquivo else nome_arquivo
            sql_content = arq.read_text(encoding="utf-8")
            checksum = calculate_checksum(sql_content)

            is_contract = "contract" in nome_arquivo.lower() or versao.upper() == "V010"

            if versao in applied:
                # Validação de integridade do arquivo já aplicado
                if applied[versao] != checksum:
                    raise SystemExit(
                        f"[Migrate FATAL] Checksum divergente para a migration {versao}!\n"
                        f"  Banco de dados: {applied[versao]}\n"
                        f"  Arquivo local:  {checksum}\n"
                        f"Arquivos de migração já aplicados não devem ser editados após a execução."
                    )
                continue

            # Se for migration de contração (destrutiva) e não houver flag explícita, ignora
            if is_contract and not allow_contract:
                print(f" [SKIP] {versao} ({nome_arquivo}) requer --allow-contract para execução.")
                continue

            pending_count += 1
            if dry_run:
                print(f" [DRY-RUN] Seria aplicada: {versao} -> {descricao}")
                continue

            print(f" [APLICANDO] {versao} — {descricao}...", end="", flush=True)
            inicio = time.time()
            statements = split_sql_statements(sql_content)

            cur_exec = conn.cursor()
            try:
                for stmt in statements:
                    cur_exec.execute(stmt)
                duracao_ms = int((time.time() - inicio) * 1000)

                cur_exec.execute(
                    """INSERT INTO schema_migrations (versao, descricao, checksum, duracao_ms)
                       VALUES (%s, %s, %s, %s)""",
                    (versao, descricao, checksum, duracao_ms),
                )
                print(f" [OK] ({duracao_ms} ms)")
            except Exception as e:
                print(f" [FALHOU]")
                cur_exec.close()
                raise SystemExit(f"[Migrate ERROR] Erro ao aplicar {versao}: {e}")
            finally:
                cur_exec.close()

        if pending_count == 0 and not dry_run:
            print("O banco de dados já está totalmente atualizado! Nenhuma migração pendente.")
        elif not dry_run:
            print(f"Sucesso! {pending_count} migração(ões) aplicada(s) com êxito.")

    finally:
        # Liberação obrigatória do lock
        try:
            cur_lock = conn.cursor()
            cur_lock.execute("SELECT RELEASE_LOCK('cuida_home_schema_migrations')")
            cur_lock.fetchall()
            cur_lock.close()
        except Exception:
            pass
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Runner de migrações MariaDB CuidaHome")
    parser.add_argument("--status", action="store_true", help="Exibe status das migrations sem aplicar")
    parser.add_argument("--dry-run", action="store_true", help="Simula aplicação sem alterar o banco")
    parser.add_argument("--allow-contract", action="store_true", help="Permite execução da fase de contração (V010)")
    args = parser.parse_args()

    run_migrations(dry_run=args.dry_run, status_only=args.status, allow_contract=args.allow_contract)


if __name__ == "__main__":
    main()
