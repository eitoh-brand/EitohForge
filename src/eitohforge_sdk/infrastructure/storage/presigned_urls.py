"""Neutral presign naming on top of get/put presigned URL hooks."""

from __future__ import annotations


class PresignedObjectUrlsMixin:
    """Adds ``generate_presigned_download`` / ``generate_presigned_upload`` as aliases.

    Implementations must define ``generate_presigned_get_url`` and ``generate_presigned_put_url``.
    """

    def generate_presigned_download(self, key: str, *, expires_in: int) -> str:
        return self.generate_presigned_get_url(key, expires_in=expires_in)

    def generate_presigned_upload(self, key: str, *, expires_in: int, content_type: str | None = None) -> str:
        return self.generate_presigned_put_url(
            key, expires_in=expires_in, content_type=content_type
        )
