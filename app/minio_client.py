"""
Cliente MinIO (Object Storage compatível com S3) — Fachada de Retrocompatibilidade
Delega todas as operações para app.services.storage preservando as assinaturas
originais utilizadas pelos módulos legados da Atividade 6.
"""

from typing import Optional
from app.services.storage import (
    get_storage_client as get_minio_client,
    ensure_buckets,
    generate_key,
    upload_file,
    delete_file,
    stream_file,
    S3_BUCKET_AVATARS as MINIO_BUCKET,
    MINIO_ENDPOINT,
    MINIO_ACCESS_KEY,
    MINIO_SECRET_KEY,
    _secure,
    S3Error,
    Minio,
)


def ensure_bucket() -> None:
    """Garante que os buckets existam (compatibilidade com Atividade 6)."""
    ensure_buckets()


def generate_object_key(user_id: int, original_filename: str) -> str:
    """Gera chave no formato legível avatars/{userId}-{timestamp}-{hex}.{ext}."""
    ext = original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else "jpg"
    return generate_key("avatars", user_id, ext)


def upload_avatar(user_id: int, file_bytes: bytes, filename: str, content_type: str) -> str:
    """Envia avatar para o bucket avatars."""
    key = generate_object_key(user_id, filename)
    return upload_file(
        bucket_name=MINIO_BUCKET,
        key=key,
        file_bytes=file_bytes,
        content_type=content_type,
    )


def delete_avatar(avatar_key: str) -> None:
    """Remove avatar do bucket avatars."""
    delete_file(MINIO_BUCKET, avatar_key)


def stream_avatar(avatar_key: str):
    """Retorna stream do avatar a partir do bucket avatars."""
    return stream_file(MINIO_BUCKET, avatar_key)


__all__ = [
    "get_minio_client",
    "ensure_bucket",
    "generate_object_key",
    "upload_avatar",
    "delete_avatar",
    "stream_avatar",
    "MINIO_BUCKET",
    "MINIO_ENDPOINT",
    "MINIO_ACCESS_KEY",
    "MINIO_SECRET_KEY",
    "S3Error",
    "Minio",
]
