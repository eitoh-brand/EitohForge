"""Secret provider factory."""

from __future__ import annotations

import os

from eitohforge_sdk.core.config import AppSettings
from eitohforge_sdk.core.secrets import (
    EnvSecretProvider,
    SecretProvider,
    UnconfiguredSecretProvider,
    VaultSecretProvider,
)


def build_secret_provider(settings: AppSettings) -> SecretProvider:
    """Build a secret provider from app settings."""
    provider_name = settings.secrets.provider
    if provider_name == "env":
        return EnvSecretProvider()
    if provider_name == "vault":
        token = os.environ.get("VAULT_TOKEN") or os.environ.get("EITOHFORGE_SECRET_VAULT_TOKEN")
        return VaultSecretProvider(
            vault_url=settings.secrets.vault_url,
            vault_mount=settings.secrets.vault_mount,
            token=token,
        )
    return UnconfiguredSecretProvider(provider_name=provider_name)

