"""
Testes automatizados do runner de migrações (db.migrate) — CuidaHome.
Compatível com unittest nativo da biblioteca padrão do Python.
"""

import unittest
from pathlib import Path
from db.migrate import split_sql_statements, calculate_checksum, MIGRATIONS_DIR


class TestMigrations(unittest.TestCase):

    def test_split_sql_statements_removes_comments_and_splits_properly(self):
        sql = """
        -- Comentário inicial
        CREATE TABLE teste (id INT PRIMARY KEY);
        # Outro comentário
        INSERT INTO teste (id) VALUES (1);
        """
        stmts = split_sql_statements(sql)
        self.assertEqual(len(stmts), 2)
        self.assertIn("CREATE TABLE teste", stmts[0])
        self.assertIn("INSERT INTO teste", stmts[1])

    def test_calculate_checksum_normalization(self):
        sql1 = "SELECT 1;\r\nSELECT 2;"
        sql2 = "SELECT 1;\nSELECT 2;"
        # Checksum deve normalizar CRLF e LF para produzir o mesmo hash
        self.assertEqual(calculate_checksum(sql1), calculate_checksum(sql2))

    def test_all_migration_files_exist_and_are_readable(self):
        files = sorted(MIGRATIONS_DIR.glob("V*.sql"))
        self.assertGreaterEqual(len(files), 10, f"Esperadas pelo menos 10 migrations, encontradas {len(files)}")

        expected_versions = [f"V{i:03d}" for i in range(1, 11)]
        found_versions = [f.name.split("__")[0] for f in files]

        for expected in expected_versions:
            self.assertIn(expected, found_versions, f"Migration {expected} ausente no diretório!")

        for f in files:
            content = f.read_text(encoding="utf-8")
            self.assertTrue(len(content.strip()) > 0, f"Migration {f.name} está vazia!")
            statements = split_sql_statements(content)
            self.assertGreaterEqual(len(statements), 1, f"Nenhum comando SQL válido extraído de {f.name}")


if __name__ == "__main__":
    unittest.main()
