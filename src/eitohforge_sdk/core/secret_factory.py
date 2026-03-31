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
from eitohforge_sdk.core.secrets_cloud import (
    AwsSecretsManagerSecretProvider,
    AzureKeyVaultSecretProvider,
    GcpSecretManagerSecretProvider,
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
    if provider_name == "aws":
        region = settings.secrets.aws_region or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"
        return AwsSecretsManagerSecretProvider(region_name=region)
    if provider_name == "azure":
        return AzureKeyVaultSecretProvider(vault_url=settings.secrets.azure_vault_url or "")
    if provider_name == "gcp":
        project = (settings.secrets.gcp_project_id or "").strip()
        if not project:
            raise ValueError(
                "EITOHFORGE_SECRET_GCP_PROJECT_ID is required when EITOHFORGE_SECRET_PROVIDER=gcp."
            )
        return GcpSecretManagerSecretProvider(project_id=project)
    return UnconfiguredSecretProvider(provider_name=provider_name)

