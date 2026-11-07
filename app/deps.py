"""
Dependências de Segurança e Controle de Acesso (RBAC / ABAC) — CuidaHome.
Fornece validadores desacoplados e reutilizáveis para injeção via Depends() no FastAPI.
"""

try:
    from fastapi import Request, HTTPException, Depends, status
except ImportError:
    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: str = ""):
            self.status_code = status_code
            self.detail = detail
            super().__init__(f"HTTP {status_code}: {detail}")

    class Request:
        pass

    def Depends(f):
        return f

    class status:
        HTTP_400_BAD_REQUEST = 400
        HTTP_401_UNAUTHORIZED = 401
        HTTP_403_FORBIDDEN = 403

try:
    from app.auth import get_current_user
except ImportError:
    async def get_current_user(request):
        return {}

try:
    from app.database import get_connection
except ImportError:
    def get_connection():
        return None


def require_roles(*allowed_roles: str):
    """
    Factory de dependência para autorização baseada em papéis (RBAC).
    Permite acesso apenas a usuários cujo papel conste em allowed_roles.
    Usuários com papéis não autorizados recebem HTTP 403 Forbidden.
    """
    async def role_checker(request: Request, user: dict = Depends(get_current_user)) -> dict:
        user_role = user.get("role", "")
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acesso negado: recurso restrito aos papéis: {', '.join(allowed_roles)}. Seu papel: '{user_role}'.",
            )
        return user
    return role_checker


async def require_verified_professional(
    request: Request,
    user: dict = Depends(get_current_user),
) -> dict:
    """
    Controle baseado em atributos (ABAC):
    Exige papel 'profissional_saude' E status_verificacao = 'aprovado' no banco.
    Profissionais com cadastro pendente ou em análise recebem HTTP 403.
    """
    if user.get("role") != "profissional_saude":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso exclusivo para profissionais de saúde.",
        )

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT status_verificacao FROM perfis_profissionais WHERE usuario_id = %s",
            (user["id"],),
        )
        row = cursor.fetchone()
        status_verificacao = row["status_verificacao"] if row else "pendente"

        if status_verificacao != "aprovado":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Acesso restrito: suas credenciais estão com status '{status_verificacao}'. "
                    "Aguarde a homologação pelo administrador para atuar em plantões."
                ),
            )
    finally:
        cursor.close()
        conn.close()

    return user


def require_owner_or_admin(resource_owner_id: int, user: dict) -> bool:
    """
    Proteção contra Insecure Direct Object References (IDOR):
    Garante que apenas o dono do recurso ou um administrador possa acessá-lo.
    """
    if user.get("role") == "admin":
        return True
    if user.get("id") == resource_owner_id:
        return True
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Acesso negado: você não tem permissão para manipular este recurso.",
    )
