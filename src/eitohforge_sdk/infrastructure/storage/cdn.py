"""CDN URL rewriting integration for public storage URLs."""

from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

from eitohforge_sdk.core.config import StorageSettings


class CdnUrlRewriter:
    """Rewrite origin public URLs to CDN URLs."""

    def __init__(self, *, origin_base_url: str, cdn_base_url: str | None = None) -> None:
        self._origin_base_url = _normalize_base_url(origin_base_url)
        self._cdn_base_url = _normalize_base_url(cdn_base_url) if cdn_base_url else None

    def build_public_url(self, key: str) -> str:
        return f"{self._origin_base_url}/{_normalize_key(key)}"

    def rewrite(self, public_url: str) -> str:
        if self._cdn_base_url is None:
            return public_url
        if not public_url.startswith(self._origin_base_url):
            return public_url
        suffix = public_url[len(self._origin_base_url) :]
        return f"{self._cdn_base_url}{suffix}"

    def build_cdn_url(self, key: str) -> str:
        return self.rewrite(self.build_public_url(key))


def build_storage_public_url(key: str, settings: StorageSettings) -> str:
    """Build public object URL and rewrite through CDN when configured."""
    origin_base_url = _resolve_origin_base_url(settings)
    rewriter = CdnUrlRewriter(origin_base_url=origin_base_url, cdn_base_url=settings.cdn_base_url)
    return rewriter.build_cdn_url(key)


def resolve_s3_origin_base_url(*, bucket_name: str, region: str, endpoint_url: str | None) -> str:
    """HTTPS origin for object keys (no trailing slash), shared by CDN builder and S3 provider."""
    if endpoint_url:
        endpoint = _normalize_base_url(endpoint_url)
        return f"{endpoint}/{bucket_name}"
    return f"https://{bucket_name}.s3.{region}.amazonaws.com"


def _resolve_origin_base_url(settings: StorageSettings) -> str:
    if settings.public_base_url:
        return settings.public_base_url
    provider = settings.provider.lower()
    if provider == "s3":
        return resolve_s3_origin_base_url(
            bucket_name=settings.bucket_name,
            region=settings.region,
            endpoint_url=settings.endpoint_url,
        )
    return "http://localhost/storage"


def _normalize_base_url(value: str) -> str:
    parsed = urlsplit(value.strip())
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"Invalid absolute URL: {value}")
    path = parsed.path.rstrip("/")
    return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))


def _normalize_key(key: str) -> str:
    normalized = key.strip().lstrip("/")
    if not normalized:
        raise ValueError("Storage key must not be empty.")
    return normalized

