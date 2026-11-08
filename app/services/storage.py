"""
Serviço de Armazenamento de Objetos S3 / Garage — CuidaHome (Atividade 9 / Fase 3)
Suporta arquitetura multi-bucket especializada:
  1. avatars: fotos de perfil públicas dos usuários.
  2. equipamentos: fotos públicas de equipamentos e acessórios ortopédicos.
  3. credenciais: documentos privados (COREN, diplomas, alvarás, certidões).
  4. documentos: laudos médicos sensíveis, termos e vistorias de locação.

Segurança:
  - Validação rigorosa de magic bytes (assinatura binária) para barrar arquivos maliciosos.
  - Limites de tamanho estritos por categoria.
  - Chaves opacas randômicas para evitar colisão e vazamento de nomes originais.
  - Garage S3 interno: documentos privados são servidos exclusivamente via proxy autenticado com RBAC.
"""

import io
import os
import secrets
import time
from typing import Optional, Tuple

try:
    from minio import Minio
    from minio.error import S3Error
except ImportError:
    class S3Error(Exception):
        """Fallback mock para ambiente local sem pacote minio instalado."""
        pass

    class Minio:
        """Fallback mock para ambiente local sem pacote minio instalado."""
        def __init__(self, *args, **kwargs):
            pass


# ── Configuração de Conexão S3 / Garage ──────────────────────────────
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "garage:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ROOT_USER", "cuidahome_admin")
MINIO_SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD", "cuidahome_secret_2026")
_secure = os.getenv("MINIO_SECURE", "false").lower() == "true"

# ── Nomes dos Buckets Especializados ────────────────────────────────
S3_BUCKET_AVATARS = os.getenv("S3_BUCKET_AVATARS", os.getenv("MINIO_BUCKET", "avatars"))
S3_BUCKET_EQUIPAMENTOS = os.getenv("S3_BUCKET_EQUIPAMENTOS", "equipamentos")
S3_BUCKET_CREDENCIAIS = os.getenv("S3_BUCKET_CREDENCIAIS", "credenciais")
S3_BUCKET_DOCUMENTOS = os.getenv("S3_BUCKET_DOCUMENTOS", "documentos")

ALL_BUCKETS = [
    S3_BUCKET_AVATARS,
    S3_BUCKET_EQUIPAMENTOS,
    S3_BUCKET_CREDENCIAIS,
    S3_BUCKET_DOCUMENTOS,
]

PUBLIC_BUCKETS = {S3_BUCKET_AVATARS, S3_BUCKET_EQUIPAMENTOS}
PRIVATE_BUCKETS = {S3_BUCKET_CREDENCIAIS, S3_BUCKET_DOCUMENTOS}

# ── Limites de Upload e Políticas de Tipo ────────────────────────────
MAX_AVATAR_BYTES = 3 * 1024 * 1024        # 3 MB
MAX_EQUIPAMENTO_BYTES = 5 * 1024 * 1024   # 5 MB
MAX_DOCUMENT_BYTES = 10 * 1024 * 1024     # 10 MB

ALLOWED_IMAGE_MIMES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}

ALLOWED_DOCUMENT_MIMES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
}

# ── Magic Bytes (Assinaturas Binárias) ───────────────────────────────
# Usadas para verificação profunda do cabeçalho binário, prevenindo renomeações maliciosas
MAGIC_SIGNATURES = {
    "application/pdf": [b"%PDF"],
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
}

# Cliente singleton
_client: Optional[Minio] = None


def get_storage_client() -> Minio:
    """Retorna o cliente S3/MinIO/Garage singleton."""
    global _client
    if _client is None:
        _client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=_secure,
        )
    return _client


def set_storage_client(client: Optional[Minio]) -> None:
    """Permite injetar cliente mock em testes unitários."""
    global _client
    _client = client


def detect_mime_type_from_magic(file_bytes: bytes) -> Optional[str]:
    """
    Analisa os primeiros bytes (magic bytes) do payload binário
    para determinar com segurança o tipo real do arquivo.
    """
    if not file_bytes:
        return None

    # Checagem de PDF (%PDF)
    if file_bytes.startswith(b"%PDF"):
        return "application/pdf"

    # Checagem de JPEG (\xFF\xD8\xFF)
    if file_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"

    # Checagem de PNG (\x89PNG\r\n\x1a\n)
    if file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"

    # Checagem de WEBP (RIFF....WEBP)
    if len(file_bytes) >= 12 and file_bytes[:4] == b"RIFF" and file_bytes[8:12] == b"WEBP":
        return "image/webp"

    return None


def validate_file_upload(
    file_bytes: bytes,
    filename: str,
    content_type: Optional[str],
    allowed_mime_types: set,
    max_bytes: int,
) -> Tuple[bool, str, str]:
    """
    Valida um arquivo de upload contra tamanho, tipo declarado e magic bytes.

    Retorna:
        (is_valid: bool, mensagem_erro_ou_mime_detectado: str, extensao_sanitizada: str)
    """
    if not file_bytes:
        return False, "Arquivo vazio não permitido.", ""

    if len(file_bytes) > max_bytes:
        limite_mb = max_bytes // (1024 * 1024)
        return False, f"Arquivo excede o limite máximo permitido de {limite_mb} MB.", ""

    detected_mime = detect_mime_type_from_magic(file_bytes)
    if not detected_mime:
        return False, "Assinatura de arquivo inválida ou formato não suportado (falha na validação de magic bytes).", ""

    if detected_mime not in allowed_mime_types:
        return False, f"Tipo de arquivo não permitido ({detected_mime}). Permitidos: {', '.join(sorted(allowed_mime_types))}.", ""

    # Mapear extensão segura a partir do MIME detectado (ignora extensão arbitrária enviada pelo cliente)
    mime_to_ext = {
        "application/pdf": "pdf",
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
    }
    ext = mime_to_ext.get(detected_mime, "bin")

    return True, detected_mime, ext


def generate_key(prefix: str, entity_id: int, extension: str) -> str:
    """
    Gera uma chave S3 única, segura e previsível para o objeto.
    Formato: {prefix}/{entity_id}/{timestamp}-{random_hex}.{ext}
    """
    clean_prefix = prefix.strip("/")
    clean_ext = extension.lstrip(".").lower() or "bin"
    timestamp = int(time.time())
    rand_hex = secrets.token_hex(6)
    return f"{clean_prefix}/{entity_id}/{timestamp}-{rand_hex}.{clean_ext}"


def ensure_buckets() -> dict:
    """
    Provisiona idempotentemente os 4 buckets especializados no Garage S3.
    Aplica política de leitura pública apenas nos buckets marcados como públicos.
    """
    client = get_storage_client()
    status = {}

    for bucket in ALL_BUCKETS:
        try:
            if not client.bucket_exists(bucket):
                client.make_bucket(bucket)
                print(f"[Storage] Bucket '{bucket}' criado com sucesso.")
            else:
                print(f"[Storage] Bucket '{bucket}' já existe.")

            # Se for bucket público, tenta definir política de leitura pública
            if bucket in PUBLIC_BUCKETS:
                policy = f"""{{
                    "Version": "2012-10-17",
                    "Statement": [
                        {{
                            "Effect": "Allow",
                            "Principal": {{"AWS": ["*"]}},
                            "Action": ["s3:GetObject"],
                            "Resource": ["arn:aws:s3:::{bucket}/*"]
                        }}
                    ]
                }}"""
                try:
                    client.set_bucket_policy(bucket, policy)
                    print(f"[Storage] Bucket '{bucket}' configurado como público.")
                except S3Error as pe:
                    print(f"[Storage] Aviso ao definir policy em '{bucket}' (Garage v0.9): {pe}")

            status[bucket] = True
        except Exception as e:
            print(f"[Storage] Erro ao provisionar bucket '{bucket}': {e}")
            status[bucket] = False

    return status


def check_storage_health() -> dict:
    """Verifica autenticação e conectividade com os buckets do Garage S3."""
    client = get_storage_client()
    results = {}
    for bucket in ALL_BUCKETS:
        try:
            exists = client.bucket_exists(bucket)
            results[bucket] = {"status": "ok", "exists": exists}
        except S3Error as e:
            results[bucket] = {
                "status": "error",
                "code": e.code,
                "message": e.message,
                "hint": "Verifique se as credenciais (MINIO_ROOT_USER e MINIO_ROOT_PASSWORD) configuradas na Stack correspondem às do serviço S3.",
            }
        except Exception as e:
            results[bucket] = {"status": "unreachable", "detail": str(e)}
    return results


def upload_file(
    bucket_name: str,
    key: str,
    file_bytes: bytes,
    content_type: str,
) -> str:
    """
    Envia binário para o bucket especificado.
    Retorna a chave gerada.
    """
    client = get_storage_client()
    client.put_object(
        bucket_name=bucket_name,
        object_name=key,
        data=io.BytesIO(file_bytes),
        length=len(file_bytes),
        content_type=content_type,
    )
    return key


def delete_file(bucket_name: str, key: str) -> None:
    """
    Remove um arquivo do bucket (best-effort, falha silenciosa com log).
    """
    if not key:
        return
    try:
        client = get_storage_client()
        client.remove_object(bucket_name, key)
    except Exception as e:
        print(f"[Storage] Aviso ao remover '{key}' do bucket '{bucket_name}': {e}")


def stream_file(bucket_name: str, key: str):
    """
    Retorna a stream do objeto para download/proxy.
    Lança S3Error caso o arquivo não seja encontrado.
    """
    client = get_storage_client()
    return client.get_object(bucket_name, key)

