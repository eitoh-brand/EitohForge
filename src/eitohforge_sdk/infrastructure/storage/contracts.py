"""Storage provider contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class StorageObject:
    """Object metadata returned by storage providers."""

    key: str
    size_bytes: int
    content_type: str | None = None


class StorageProvider(Protocol):
    """Storage provider interface."""

    def put_bytes(self, key: str, data: bytes, *, content_type: str | None = None) -> StorageObject:
        ...

    def get_bytes(self, key: str) -> bytes:
        ...

    def delete(self, key: str) -> bool:
        ...

    def exists(self, key: str) -> bool:
        ...


class PresignableStorageProvider(StorageProvider, Protocol):
    """Storage provider that can generate presigned access URLs."""

    def generate_presigned_get_url(self, key: str, *, expires_in: int) -> str:
        ...

    def generate_presigned_put_url(
        self, key: str, *, expires_in: int, content_type: str | None = None
    ) -> str:
        ...

