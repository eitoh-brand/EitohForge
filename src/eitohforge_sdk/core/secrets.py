"""Secret provider abstraction and provider factory."""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Protocol


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

