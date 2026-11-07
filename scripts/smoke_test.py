"""
Script de validação automatizada (Smoke Test) pós-deploy — CuidaHome.
Uso:
    python scripts/smoke_test.py [--base-url http://localhost:8210]
"""

import sys
import argparse
import urllib.request
import urllib.error
import json


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def check_url(url: str, expected_statuses: tuple = (200,)) -> tuple[bool, int, str]:
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "CuidaHome-SmokeTest/1.0"},
        )
        opener = urllib.request.build_opener(NoRedirectHandler)
        with opener.open(req, timeout=10) as response:
            status = response.getcode()
            body = response.read().decode("utf-8", errors="ignore")
            return (status in expected_statuses, status, body)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        return (e.code in expected_statuses, e.code, body)
    except Exception as e:
        return (False, 0, str(e))


def main():
    parser = argparse.ArgumentParser(description="Smoke test da plataforma CuidaHome")
    parser.add_argument("--base-url", default="http://localhost:8210", help="URL base da aplicação")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    print(f"==================================================")
    print(f"Iniciando Smoke Test CuidaHome em: {base_url}")
    print(f"==================================================")

    tests = [
        ("Healthcheck do Catalog Service", f"{base_url}/health", (200,), ["status", "ok"]),
        ("Página Inicial / Landing Page", f"{base_url}/", (200,), ["CuidaHome", "Saúde"]),
        ("Redirecionamento do catálogo antigo (/catalog)", f"{base_url}/catalog", (200, 301, 302), []),
        ("Proteção da área de família sem login", f"{base_url}/painel/familia", (302, 401, 403), []),
    ]

    failed = 0
    for name, url, valid_statuses, expected_substrings in tests:
        success, status, body = check_url(url, valid_statuses)
        content_ok = True
        missing_substr = None

        if success and expected_substrings:
            for s in expected_substrings:
                if s.lower() not in body.lower():
                    content_ok = False
                    missing_substr = s
                    break

        if success and content_ok:
            print(f" [PASS] {name} (HTTP {status})")
        else:
            failed += 1
            reason = f"HTTP {status}" if not success else f"Conteúdo ausente: '{missing_substr}'"
            print(f" [FAIL] {name} -> {reason}")

    print("--------------------------------------------------")
    if failed == 0:
        print("RESULTADO: Todos os testes passaram com sucesso! (100% OK)")
        sys.exit(0)
    else:
        print(f"RESULTADO: {failed} teste(s) falharam.")
        sys.exit(1)


if __name__ == "__main__":
    main()

