"""Azure Blob storage (optional ``azure-storage-blob``)."""

from __future__ import annotations

import importlib
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from eitohforge_sdk.infrastructure.storage.contracts import StorageObject
from eitohforge_sdk.infrastructure.storage.presigned_urls import PresignedObjectUrlsMixin


def _azure_blob_types() -> tuple[Any, Any, Any, Any]:
    try:
        mod = importlib.import_module("azure.storage.blob")
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Azure blob storage requires 'azure-storage-blob'. "
            "Install via `pip install eitohforge[azure-storage]` or `pip install azure-storage-blob`."
        ) from exc
    BlobServiceClient = getattr(mod, "BlobServiceClient")
    generate_blob_sas = getattr(mod, "generate_blob_sas")
    BlobSasPermissions = getattr(mod, "BlobSasPermissions")
    ContentSettings = getattr(mod, "ContentSettings")
    return BlobServiceClient, generate_blob_sas, BlobSasPermissions, ContentSettings


def _account_name_key_from_connection_string(connection_string: str) -> tuple[str, str]:
    parts: dict[str, str] = {}
    for segment in connection_string.split(";"):
        segment = segment.strip()
        if not segment or "=" not in segment:
            continue
        seg_key, value = segment.split("=", 1)
        parts[seg_key.strip()] = value.strip()
    account_name = parts.get("AccountName")
    account_key = parts.get("AccountKey")
    if not account_name or not account_key:
        raise ValueError(
            "Azure connection string must include AccountName and AccountKey for SAS URL generation."
        )
    return account_name, account_key


class AzureBlobStorageProvider(PresignedObjectUrlsMixin):
    """Azure Blob container as object storage (container name = ``bucket_name`` in settings)."""

    def __init__(
        self,
        *,
        connection_string: str,
        container_name: str,
        public_base_url: str | None = None,
        client: Any | None = None,
    ) -> None:
        BlobServiceClient, _, _, _ = _azure_blob_types()
        self._container_name = container_name
        self._public_base_url = public_base_url.rstrip("/") if public_base_url else None
        self._service = client or BlobServiceClient.from_connection_string(connection_string)
        self._account_name, self._account_key = _account_name_key_from_connection_string(
            connection_string
        )
        self._container_client = self._service.get_container_client(container_name)

    def put_bytes(self, key: str, data: bytes, *, content_type: str | None = None) -> StorageObject:
        _, _, _, ContentSettings = _azure_blob_types()
        blob = self._container_client.get_blob_client(key)
        kwargs: dict[str, Any] = {}
        if content_type is not None:
            kwargs["content_settings"] = ContentSettings(content_type=content_type)
        blob.upload_blob(data, overwrite=True, **kwargs)
        return StorageObject(key=key, size_bytes=len(data), content_type=content_type)

    def get_bytes(self, key: str) -> bytes:
        blob = self._container_client.get_blob_client(key)
        return cast(bytes, blob.download_blob().readall())

    def delete(self, key: str) -> bool:
        blob = self._container_client.get_blob_client(key)
        try:
            blob.delete_blob()
        except Exception:
            return False
        return True

    def exists(self, key: str) -> bool:
        blob = self._container_client.get_blob_client(key)
        return bool(blob.exists())

    def generate_presigned_get_url(self, key: str, *, expires_in: int) -> str:
        _, generate_blob_sas, BlobSasPermissions, _ = _azure_blob_types()
        expiry = datetime.now(UTC) + timedelta(seconds=expires_in)
        sas = generate_blob_sas(
            account_name=self._account_name,
            container_name=self._container_name,
            blob_name=key,
            account_key=self._account_key,
            permission=BlobSasPermissions(read=True),
            expiry=expiry,
        )
        blob = self._container_client.get_blob_client(key)
        return f"{blob.url}?{sas}"

    def generate_presigned_put_url(
        self, key: str, *, expires_in: int, content_type: str | None = None
    ) -> str:
        _, generate_blob_sas, BlobSasPermissions, _ = _azure_blob_types()
        expiry = datetime.now(UTC) + timedelta(seconds=expires_in)
        sas = generate_blob_sas(
            account_name=self._account_name,
            container_name=self._container_name,
            blob_name=key,
            account_key=self._account_key,
            permission=BlobSasPermissions(write=True, create=True),
            expiry=expiry,
            content_type=content_type,
        )
        blob = self._container_client.get_blob_client(key)
        return f"{blob.url}?{sas}"

    def generate_public_url(self, key: str) -> str:
        if self._public_base_url:
            clean = key.strip().lstrip("/")
            return f"{self._public_base_url}/{clean}"
        blob = self._container_client.get_blob_client(key)
        return cast(str, blob.url)
