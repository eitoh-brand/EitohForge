"""Tenant-scoped storage provider wrappers.

Phase 18: tenant storage prefix.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from eitohforge_sdk.core.tenant import TenantContext
from eitohforge_sdk.infrastructure.storage.contracts import (
    PresignableStorageProvider,
    StorageObject,
    StorageProvider,
)


@dataclass(frozen=True)
class TenantScopedStorageProvider:
    """Prefix storage keys with the current tenant id (best-effort)."""

    delegate: StorageProvider
    separator: str = "/"

    def _tenant_id_prefix(self) -> str | None:
        tenant_id = TenantContext.current().tenant_id
        if tenant_id is None:
            return None
        tenant_id = tenant_id.strip()
        if not tenant_id:
            return None
        return f"{tenant_id}{self.separator}"

    def _namespaced_key(self, key: str) -> str:
        prefix = self._tenant_id_prefix()
        if prefix is None:
            return key
        clean_key = key.strip().lstrip("/")
        if not clean_key:
            return key
        if clean_key.startswith(prefix):
            return key
        return f"{prefix}{clean_key}"

    def put_bytes(self, key: str, data: bytes, *, content_type: str | None = None) -> StorageObject:
        namespaced = self._namespaced_key(key)
        return self.delegate.put_bytes(namespaced, data, content_type=content_type)

    def get_bytes(self, key: str) -> bytes:
        return self.delegate.get_bytes(self._namespaced_key(key))

    def delete(self, key: str) -> bool:
        return self.delegate.delete(self._namespaced_key(key))

    def exists(self, key: str) -> bool:
        return self.delegate.exists(self._namespaced_key(key))

    def generate_presigned_get_url(self, key: str, *, expires_in: int) -> str:
        delegate = self._as_presignable_delegate()
        return delegate.generate_presigned_get_url(self._namespaced_key(key), expires_in=expires_in)

    def generate_presigned_put_url(
        self, key: str, *, expires_in: int, content_type: str | None = None
    ) -> str:
        delegate = self._as_presignable_delegate()
        return delegate.generate_presigned_put_url(
            self._namespaced_key(key), expires_in=expires_in, content_type=content_type
        )

    def _as_presignable_delegate(self) -> PresignableStorageProvider:
        delegate = self.delegate
        if not hasattr(delegate, "generate_presigned_get_url") or not hasattr(
            delegate, "generate_presigned_put_url"
        ):
            raise TypeError("Underlying storage provider does not support presigned URLs.")
        return cast(PresignableStorageProvider, delegate)

