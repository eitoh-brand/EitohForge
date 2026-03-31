"""Google Cloud Storage (optional ``google-cloud-storage``)."""

from __future__ import annotations

import importlib
from datetime import timedelta
from typing import Any, cast

from eitohforge_sdk.infrastructure.storage.contracts import StorageObject
from eitohforge_sdk.infrastructure.storage.presigned_urls import PresignedObjectUrlsMixin


def _storage_client(*, project: str | None) -> Any:
    try:
        gcs = importlib.import_module("google.cloud.storage")
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "GCS storage requires 'google-cloud-storage'. "
            "Install via `pip install eitohforge[gcs]` or `pip install google-cloud-storage`."
        ) from exc
    return gcs.Client(project=project)


class GcsStorageProvider(PresignedObjectUrlsMixin):
    """GCS bucket as object storage."""

    def __init__(
        self,
        *,
        bucket_name: str,
        project: str | None = None,
        public_base_url: str | None = None,
        client: Any | None = None,
    ) -> None:
        self._client = client or _storage_client(project=project)
        self._bucket = self._client.bucket(bucket_name)
        self._public_base_url = public_base_url.rstrip("/") if public_base_url else None

    def put_bytes(self, key: str, data: bytes, *, content_type: str | None = None) -> StorageObject:
        blob = self._bucket.blob(key)
        blob.upload_from_string(data, content_type=content_type)
        return StorageObject(key=key, size_bytes=len(data), content_type=content_type)

    def get_bytes(self, key: str) -> bytes:
        blob = self._bucket.blob(key)
        return cast(bytes, blob.download_as_bytes())

    def delete(self, key: str) -> bool:
        blob = self._bucket.blob(key)
        try:
            blob.delete()
        except Exception:
            return False
        return True

    def exists(self, key: str) -> bool:
        blob = self._bucket.blob(key)
        return bool(blob.exists())

    def generate_presigned_get_url(self, key: str, *, expires_in: int) -> str:
        blob = self._bucket.blob(key)
        return str(
            blob.generate_signed_url(
                version="v4",
                expiration=timedelta(seconds=expires_in),
                method="GET",
            )
        )

    def generate_presigned_put_url(
        self, key: str, *, expires_in: int, content_type: str | None = None
    ) -> str:
        blob = self._bucket.blob(key)
        return str(
            blob.generate_signed_url(
                version="v4",
                expiration=timedelta(seconds=expires_in),
                method="PUT",
                content_type=content_type,
            )
        )

    def generate_public_url(self, key: str) -> str:
        if self._public_base_url:
            clean = key.strip().lstrip("/")
            return f"{self._public_base_url}/{clean}"
        clean = key.strip().lstrip("/")
        return f"https://storage.googleapis.com/{self._bucket.name}/{clean}"
