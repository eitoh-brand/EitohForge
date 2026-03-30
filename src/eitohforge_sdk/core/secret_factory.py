"""Secret provider factory."""

from eitohforge_sdk.core.config import AppSettings
from eitohforge_sdk.core.secrets import EnvSecretProvider, SecretProvider, UnconfiguredSecretProvider


def build_secret_provider(settings: AppSettings) -> SecretProvider:
    """Build a secret provider from app settings."""
    provider_name = settings.secrets.provider
    if provider_name == "env":
        return EnvSecretProvider()
    return UnconfiguredSecretProvider(provider_name=provider_name)

