"""Optional cloud secret providers (AWS Secrets Manager, Azure Key Vault REST)."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
import urllib.error
import urllib.request


@dataclass
class AwsSecretsManagerSecretProvider:
    """Resolve secrets from AWS Secrets Manager (requires optional ``boto3``)."""

    region_name: str

    def get(self, key: str) -> str | None:
        try:
            import boto3  # type: ignore[import-not-found]
            from botocore.exceptions import ClientError  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ImportError(
                "Install boto3 to use AwsSecretsManagerSecretProvider: pip install boto3"
            ) from exc

        client = boto3.client("secretsmanager", region_name=self.region_name)
        try:
            resp: dict[str, object] = client.get_secret_value(SecretId=key)
        except ClientError:
            return None
        secret_string = resp.get("SecretString")
        if isinstance(secret_string, str) and secret_string:
            return secret_string
        if secret_string not in (None, ""):
            return str(secret_string)
        secret_binary = resp.get("SecretBinary")
        if isinstance(secret_binary, (bytes, bytearray)) and secret_binary:
            return secret_binary.decode("utf-8", errors="replace")
        if secret_binary not in (None, b""):
            return str(secret_binary)
        return None


@dataclass
class AzureKeyVaultSecretProvider:
    """Resolve secrets from Azure Key Vault using REST + bearer token.

    Set ``AZURE_KEY_VAULT_TOKEN`` (or pass ``access_token``) to an AAD access token for
    ``https://vault.azure.net/.default`` scope. For local dev, use ``az account get-access-token``.
    """

    vault_url: str
    access_token: str | None = None

    def get(self, key: str) -> str | None:
        token = self.access_token or os.environ.get("AZURE_KEY_VAULT_TOKEN")
        if not token:
            return None
        base = self.vault_url.rstrip("/")
        # key may be "my-secret" or "path/to/secret"
        path = key.strip("/").replace("//", "/")
        url = f"{base}/secrets/{path}?api-version=7.4"
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = resp.read().decode("utf-8")
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
            return None
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return None
        val = data.get("value")
        return str(val) if val is not None else None
