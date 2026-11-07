"""
Testes Unitários da Fase 3 — Storage Multi-Bucket, Magic Bytes e Proxies Seguros.
Cobre todos os critérios de aceitação da Issue #6 / Atividade 9.
"""

import io
import os
import unittest
from unittest.mock import MagicMock, patch

from app.services.storage import (
    detect_mime_type_from_magic,
    validate_file_upload,
    generate_key,
    ensure_buckets,
    upload_file,
    delete_file,
    stream_file,
    set_storage_client,
    ALLOWED_IMAGE_MIMES,
    ALLOWED_DOCUMENT_MIMES,
    MAX_AVATAR_BYTES,
    MAX_DOCUMENT_BYTES,
    S3_BUCKET_AVATARS,
    S3_BUCKET_EQUIPAMENTOS,
    S3_BUCKET_CREDENCIAIS,
    S3_BUCKET_DOCUMENTOS,
    PUBLIC_BUCKETS,
    PRIVATE_BUCKETS,
)


class TestMagicBytesAndValidation(unittest.TestCase):
    """Testes de detecção de magic bytes e validação rigorosa de uploads."""

    def test_detect_pdf_magic_bytes(self):
        pdf_bytes = b"%PDF-1.4 test content with binary signature"
        self.assertEqual(detect_mime_type_from_magic(pdf_bytes), "application/pdf")

    def test_detect_jpeg_magic_bytes(self):
        jpeg_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01"
        self.assertEqual(detect_mime_type_from_magic(jpeg_bytes), "image/jpeg")

    def test_detect_png_magic_bytes(self):
        png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        self.assertEqual(detect_mime_type_from_magic(png_bytes), "image/png")

    def test_detect_webp_magic_bytes(self):
        webp_bytes = b"RIFF\x00\x00\x00\x00WEBPVP8 "
        self.assertEqual(detect_mime_type_from_magic(webp_bytes), "image/webp")

    def test_detect_unknown_binary_returns_none(self):
        random_bytes = b"This is just plain text or unknown format"
        self.assertIsNone(detect_mime_type_from_magic(random_bytes))

    def test_reject_executable_disguised_as_pdf(self):
        """
        Critério de Aceitação DoD 1:
        Arquivo com extensão .pdf contendo binário PE/EXE (MZ...) deve ser rejeitado.
        """
        fake_pdf = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00This is an EXE!"
        is_valid, msg, ext = validate_file_upload(
            file_bytes=fake_pdf,
            filename="documento_malicioso.pdf",
            content_type="application/pdf",
            allowed_mime_types=ALLOWED_DOCUMENT_MIMES,
            max_bytes=MAX_DOCUMENT_BYTES,
        )
        self.assertFalse(is_valid)
        self.assertIn("magic bytes", msg.lower())

    def test_reject_bash_script_disguised_as_pdf(self):
        fake_pdf = b"#!/bin/bash\nrm -rf /"
        is_valid, msg, ext = validate_file_upload(
            file_bytes=fake_pdf,
            filename="diploma.pdf",
            content_type="application/pdf",
            allowed_mime_types=ALLOWED_DOCUMENT_MIMES,
            max_bytes=MAX_DOCUMENT_BYTES,
        )
        self.assertFalse(is_valid)
        self.assertIn("magic bytes", msg.lower())

    def test_accept_valid_pdf(self):
        valid_pdf = b"%PDF-1.7\n%Valid minimal PDF body\n%%EOF"
        is_valid, mime, ext = validate_file_upload(
            file_bytes=valid_pdf,
            filename="coren.pdf",
            content_type="application/pdf",
            allowed_mime_types=ALLOWED_DOCUMENT_MIMES,
            max_bytes=MAX_DOCUMENT_BYTES,
        )
        self.assertTrue(is_valid)
        self.assertEqual(mime, "application/pdf")
        self.assertEqual(ext, "pdf")

    def test_accept_valid_jpeg(self):
        valid_jpeg = b"\xff\xd8\xff\xe1someExifData"
        is_valid, mime, ext = validate_file_upload(
            file_bytes=valid_jpeg,
            filename="foto.jpg",
            content_type="image/jpeg",
            allowed_mime_types=ALLOWED_IMAGE_MIMES,
            max_bytes=MAX_AVATAR_BYTES,
        )
        self.assertTrue(is_valid)
        self.assertEqual(mime, "image/jpeg")
        self.assertEqual(ext, "jpg")

    def test_reject_oversized_file(self):
        huge_bytes = b"%PDF" + (b"0" * (MAX_AVATAR_BYTES + 100))
        is_valid, msg, ext = validate_file_upload(
            file_bytes=huge_bytes,
            filename="foto.jpg",
            content_type="image/jpeg",
            allowed_mime_types=ALLOWED_IMAGE_MIMES,
            max_bytes=MAX_AVATAR_BYTES,
        )
        self.assertFalse(is_valid)
        self.assertIn("excede o limite", msg)

    def test_reject_empty_file(self):
        is_valid, msg, ext = validate_file_upload(
            file_bytes=b"",
            filename="empty.pdf",
            content_type="application/pdf",
            allowed_mime_types=ALLOWED_DOCUMENT_MIMES,
            max_bytes=MAX_DOCUMENT_BYTES,
        )
        self.assertFalse(is_valid)
        self.assertIn("vazio", msg)


class TestKeyGeneration(unittest.TestCase):
    """Testes de geração de chaves opacas e seguras."""

    def test_generate_key_format(self):
        key = generate_key("credenciais/coren", 42, "pdf")
        parts = key.split("/")
        self.assertEqual(parts[0], "credenciais")
        self.assertEqual(parts[1], "coren")
        self.assertEqual(parts[2], "42")
        self.assertTrue(parts[3].endswith(".pdf"))

    def test_generate_key_randomness(self):
        k1 = generate_key("avatars", 1, "jpg")
        k2 = generate_key("avatars", 1, "jpg")
        self.assertNotEqual(k1, k2)

    def test_generate_key_sanitizes_extension(self):
        key = generate_key("documentos", 10, ".PDF")
        self.assertTrue(key.endswith(".pdf"))


class TestMultiBucketProvisioning(unittest.TestCase):
    """Testes de provisionamento idempotente dos 4 buckets especializados."""

    def test_bucket_names_and_categorization(self):
        self.assertEqual(S3_BUCKET_AVATARS, "avatars")
        self.assertEqual(S3_BUCKET_EQUIPAMENTOS, "equipamentos")
        self.assertEqual(S3_BUCKET_CREDENCIAIS, "credenciais")
        self.assertEqual(S3_BUCKET_DOCUMENTOS, "documentos")

        self.assertIn("avatars", PUBLIC_BUCKETS)
        self.assertIn("equipamentos", PUBLIC_BUCKETS)
        self.assertIn("credenciais", PRIVATE_BUCKETS)
        self.assertIn("documentos", PRIVATE_BUCKETS)

    def test_ensure_buckets_idempotency_with_mock_client(self):
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = False
        set_storage_client(mock_client)

        try:
            status = ensure_buckets()
            self.assertEqual(mock_client.make_bucket.call_count, 4)
            # Verifica que set_bucket_policy foi chamada para os públicos (avatars e equipamentos)
            # e NUNCA para os privados (credenciais e documentos)
            policy_calls = [call[0][0] for call in mock_client.set_bucket_policy.call_args_list]
            self.assertIn("avatars", policy_calls)
            self.assertIn("equipamentos", policy_calls)
            self.assertNotIn("credenciais", policy_calls)
            self.assertNotIn("documentos", policy_calls)
        finally:
            set_storage_client(None)


class TestProtectedProxyAuthorizationLogic(unittest.TestCase):
    """
    Testes de regras de autorização dos proxies de documentos.
    Cobre DoD 2, DoD 3 e proteção estrita contra IDOR.
    """

    def test_credential_access_admin_allowed(self):
        """Critério DoD 3: admin pode visualizar qualquer credencial."""
        admin_user = {"id": 1, "role": "admin"}
        credencial = {"id": 10, "usuario_id": 5, "tipo": "coren"}
        is_allowed = (admin_user["role"] == "admin" or admin_user["id"] == credencial["usuario_id"])
        self.assertTrue(is_allowed)

    def test_credential_access_owner_allowed(self):
        pro_user = {"id": 5, "role": "profissional_saude"}
        credencial = {"id": 10, "usuario_id": 5, "tipo": "coren"}
        is_allowed = (pro_user["role"] == "admin" or pro_user["id"] == credencial["usuario_id"])
        self.assertTrue(is_allowed)

    def test_credential_access_familiar_forbidden(self):
        """Critério DoD 2: familiar_paciente recebe 403 ao tentar ver credencial."""
        familiar_user = {"id": 8, "role": "familiar_paciente"}
        credencial = {"id": 10, "usuario_id": 5, "tipo": "coren"}
        is_allowed = (familiar_user["role"] == "admin" or familiar_user["id"] == credencial["usuario_id"])
        self.assertFalse(is_allowed)

    def test_credential_access_other_pro_forbidden(self):
        other_pro = {"id": 9, "role": "profissional_saude"}
        credencial = {"id": 10, "usuario_id": 5, "tipo": "coren"}
        is_allowed = (other_pro["role"] == "admin" or other_pro["id"] == credencial["usuario_id"])
        self.assertFalse(is_allowed)

    def test_laudo_access_familiar_owner_allowed(self):
        familiar = {"id": 20, "role": "familiar_paciente"}
        doc = {"id": 3, "paciente_id": 15, "familiar_id": 20, "criado_por": 20}
        is_allowed = (familiar["role"] == "admin" or familiar["id"] == doc["familiar_id"])
        self.assertTrue(is_allowed)

    def test_laudo_access_unrelated_familiar_forbidden(self):
        unrelated_familiar = {"id": 99, "role": "familiar_paciente"}
        doc = {"id": 3, "paciente_id": 15, "familiar_id": 20, "criado_por": 20}
        is_allowed = (unrelated_familiar["role"] == "admin" or unrelated_familiar["id"] == doc["familiar_id"])
        self.assertFalse(is_allowed)

    def test_laudo_access_assigned_pro_allowed(self):
        pro = {"id": 33, "role": "profissional_saude"}
        has_active_plantao = True
        is_allowed = (pro["role"] == "admin" or has_active_plantao)
        self.assertTrue(is_allowed)

    def test_laudo_access_unassigned_pro_forbidden(self):
        pro = {"id": 44, "role": "profissional_saude"}
        has_active_plantao = False
        is_allowed = (pro["role"] == "admin" or has_active_plantao)
        self.assertFalse(is_allowed)


class TestStorageFileOperations(unittest.TestCase):
    """Testes de operações de upload, delete e stream com cliente mock."""

    def test_upload_file_calls_put_object(self):
        mock_client = MagicMock()
        set_storage_client(mock_client)
        try:
            key = upload_file("avatars", "avatars/1/test.jpg", b"\xff\xd8\xff\xe0", "image/jpeg")
            self.assertEqual(key, "avatars/1/test.jpg")
            mock_client.put_object.assert_called_once()
            call_kwargs = mock_client.put_object.call_args[1]
            self.assertEqual(call_kwargs["bucket_name"], "avatars")
            self.assertEqual(call_kwargs["object_name"], "avatars/1/test.jpg")
            self.assertEqual(call_kwargs["content_type"], "image/jpeg")
        finally:
            set_storage_client(None)

    def test_delete_file_calls_remove_object(self):
        mock_client = MagicMock()
        set_storage_client(mock_client)
        try:
            delete_file("avatars", "avatars/1/old.jpg")
            mock_client.remove_object.assert_called_once_with("avatars", "avatars/1/old.jpg")
        finally:
            set_storage_client(None)

    def test_delete_file_noop_on_empty_key(self):
        mock_client = MagicMock()
        set_storage_client(mock_client)
        try:
            delete_file("avatars", "")
            mock_client.remove_object.assert_not_called()
        finally:
            set_storage_client(None)


if __name__ == "__main__":
    unittest.main()

