"""Neutral presign naming on top of get/put presigned URL hooks."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class _PresignUrlHooks(Protocol):
    """Methods required for :class:`PresignedObjectUrlsMixin` alias methods."""

    def generate_presigned_get_url(self, key: str, *, expires_in: int) -> str: ...

    def generate_presigned_put_url(
        self, key: str, *, expires_in: int, content_type: str | None = None
    ) -> str: ...


class PresignedObjectUrlsMixin:
    """Adds ``generate_presigned_download`` / ``generate_presigned_upload`` as aliases.

    Implementations must define ``generate_presigned_get_url`` and ``generate_presigned_put_url``.
    """

    def generate_presigned_download(self: _PresignUrlHooks, key: str, *, expires_in: int) -> str:
        return self.generate_presigned_get_url(key, expires_in=expires_in)

    def generate_presigned_upload(
        self: _PresignUrlHooks, key: str, *, expires_in: int, content_type: str | None = None
    ) -> str:
        return self.generate_presigned_put_url(
            key, expires_in=expires_in, content_type=content_type
        )
