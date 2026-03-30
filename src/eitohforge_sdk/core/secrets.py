"""Secret provider abstraction and provider implementations."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Any, Protocol
import urllib.error
import urllib.request
from urllib.parse import quote


class SecretNotFoundError(KeyError):
    """Raised when a required secret is missing."""


class SecretProvider(Protocol):
    """Contract for retrieving secret values by key."""

    def get(self, key: str) -> str | None:
        """Return secret value or None if absent."""


def require_secret(provider: SecretProvider, key: str) -> str:
    """Return a required secret or raise if missing."""
    value = provider.get(key)
    if value is None:
        raise SecretNotFoundError(f"Missing required secret: {key}")
    return value


@dataclass
class EnvSecretProvider:
    """Resolve secrets from process environment variables."""

    def get(self, key: str) -> str | None:
        return os.environ.get(key)


@dataclass
class DictSecretProvider:
    """In-memory provider for tests and local tooling."""

    values: dict[str, str]

    def get(self, key: str) -> str | None:
        return self.values.get(key)


@dataclass
class UnconfiguredSecretProvider:
    """Placeholder provider for future managed secret adapters."""

    provider_name: str

    def get(self, key: str) -> str | None:
        raise NotImplementedError(
            f"Secret provider '{self.provider_name}' is not implemented yet for key: {key}"
        )


def _quote_secret_path(path: str) -> str:
    # Vault secret paths may contain slashes; quote each segment while preserving `/`.
    segments = [seg for seg in path.strip("/").split("/") if seg]
    return "/".join(quote(seg, safe="") for seg in segments)


@dataclass
class VaultSecretProvider:
    """HashiCorp Vault KV provider (best-effort).

    This implementation targets the common KV shapes:
    - KV v2: `/v1/{mount}/data/{path}` with response `{ "data": { "data": { ... }}}`
    - KV v1: `/v1/{mount}/{path}` with response `{ "data": { ... }}`

    Secret value extraction rules:
    - If the returned map contains `value`, return that.
    - Else if it contains a field matching `key`, return that.
    - Else if the map contains exactly one entry, return its sole value.
    - Otherwise return `None`.
    """

    vault_url: str | None
    vault_mount: str = "secret"
    token: str | None = None

    def get(self, key: str) -> str | None:
        if not self.vault_url or not self.token:
            return None
        base = self.vault_url.rstrip("/")
        mount = self.vault_mount.strip("/")
        secret_path = _quote_secret_path(key)

        # Try KV v2 first.
        v2_value = self._get_kv2_value(base=base, mount=mount, secret_path=secret_path, key=key)
        if v2_value is not None:
            return v2_value

        # Fallback to KV v1.
        return self._get_kv1_value(base=base, mount=mount, secret_path=secret_path, key=key)

    def _get_kv2_value(
        self, *, base: str, mount: str, secret_path: str, key: str
    ) -> str | None:
        url = f"{base}/v1/{mount}/data/{secret_path}"
        data = self._fetch_json(url)
        if data is None:
            return None
        fields = data.get("data", {}).get("data")
        if not isinstance(fields, dict):
            return None
        return _extract_secret_value(key=key, fields=fields)

    def _get_kv1_value(
        self, *, base: str, mount: str, secret_path: str, key: str
    ) -> str | None:
        url = f"{base}/v1/{mount}/{secret_path}"
        data = self._fetch_json(url)
        if data is None:
            return None
        fields = data.get("data")
        if not isinstance(fields, dict):
            return None
        return _extract_secret_value(key=key, fields=fields)

    def _fetch_json(self, url: str) -> dict[str, Any] | None:
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "X-Vault-Token": self.token or "",
                    "Accept": "application/json",
                },
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                raw = resp.read().decode("utf-8")
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else None
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return None


def _extract_secret_value(*, key: str, fields: dict[str, Any]) -> str | None:
    if "value" in fields and fields["value"] is not None:
        return str(fields["value"])
    if key in fields and fields[key] is not None:
        return str(fields[key])
    if len(fields) == 1:
        sole = next(iter(fields.values()))
        return str(sole) if sole is not None else None
    return None

