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
    """Storage provider that can generate presigned access URLs.

    Implementations may also expose neutral names via ``PresignedObjectUrlsMixin``:

    - ``generate_presigned_download`` → get URL
    - ``generate_presigned_upload`` → put URL

    Object stores that know a stable HTTPS layout may implement ``generate_public_url``.
    """

    def generate_presigned_get_url(self, key: str, *, expires_in: int) -> str:
        ...

    def generate_presigned_put_url(
        self, key: str, *, expires_in: int, content_type: str | None = None
    ) -> str:
        ...

