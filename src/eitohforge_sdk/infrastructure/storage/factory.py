"""Storage provider factory."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from eitohforge_sdk.core.config import AppSettings, StorageSettings
from eitohforge_sdk.infrastructure.storage.contracts import StorageProvider
from eitohforge_sdk.infrastructure.storage.local import LocalStorageProvider
from eitohforge_sdk.infrastructure.storage.s3 import S3StorageProvider
from eitohforge_sdk.infrastructure.storage.tenant_scoped import TenantScopedStorageProvider


def build_storage_provider(
    settings: AppSettings,
    *,
    local_root_path: Path | None = None,
    s3_client: Any | None = None,
) -> StorageProvider:
    """Build a storage provider from app settings."""
    delegate = _build_storage_provider_for_settings(
        settings.storage,
        local_root_path=local_root_path,
        s3_client=s3_client,
    )
    if settings.tenant.enabled:
        return TenantScopedStorageProvider(delegate=delegate)
    return delegate


def _build_storage_provider_for_settings(
    settings: StorageSettings, *, local_root_path: Path | None, s3_client: Any | None
) -> StorageProvider:
    provider = settings.provider.lower()
    if provider == "local":
        root_path = local_root_path or Path(".eitohforge/storage")
        return LocalStorageProvider(root_path=root_path)
    if provider == "s3":
        return S3StorageProvider(
            bucket_name=settings.bucket_name,
            region=settings.region,
            endpoint_url=settings.endpoint_url,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            aws_session_token=settings.aws_session_token,
            client=s3_client,
        )
    raise ValueError(f"Unsupported storage provider: {settings.provider}")

