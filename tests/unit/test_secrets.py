import pytest
import json

from eitohforge_sdk.core.config import AppSettings
from eitohforge_sdk.core.secret_factory import build_secret_provider
from eitohforge_sdk.core.secrets import (
    DictSecretProvider,
    EnvSecretProvider,
    SecretNotFoundError,
    VaultSecretProvider,
    require_secret,
)
from eitohforge_sdk.core.secrets_cloud import GcpSecretManagerSecretProvider


def test_env_secret_provider_reads_process_environment(monkeypatch) -> None:
    monkeypatch.setenv("SERVICE_TOKEN", "token-123")
    provider = EnvSecretProvider()
    assert provider.get("SERVICE_TOKEN") == "token-123"


def test_require_secret_raises_when_missing() -> None:
    provider = DictSecretProvider(values={})
    with pytest.raises(SecretNotFoundError):
        require_secret(provider, "MISSING")


def test_secret_factory_builds_env_provider(monkeypatch) -> None:
    monkeypatch.setenv("EITOHFORGE_AUTH_JWT_SECRET", "x" * 32)
    monkeypatch.setenv("EITOHFORGE_SECRET_PROVIDER", "env")
    settings = AppSettings()
    provider = build_secret_provider(settings)
    assert isinstance(provider, EnvSecretProvider)


def test_secret_factory_builds_gcp_provider(monkeypatch) -> None:
    monkeypatch.setenv("EITOHFORGE_AUTH_JWT_SECRET", "x" * 32)
    monkeypatch.setenv("EITOHFORGE_SECRET_PROVIDER", "gcp")
    monkeypatch.setenv("EITOHFORGE_SECRET_GCP_PROJECT_ID", "my-gcp-project")
    settings = AppSettings()
    provider = build_secret_provider(settings)
    assert isinstance(provider, GcpSecretManagerSecretProvider)


def test_secret_factory_gcp_requires_project_id(monkeypatch) -> None:
    monkeypatch.setenv("EITOHFORGE_AUTH_JWT_SECRET", "x" * 32)
    monkeypatch.setenv("EITOHFORGE_SECRET_PROVIDER", "gcp")
    monkeypatch.delenv("EITOHFORGE_SECRET_GCP_PROJECT_ID", raising=False)
    settings = AppSettings()
    with pytest.raises(ValueError, match="GCP_PROJECT_ID"):
        build_secret_provider(settings)


def test_secret_factory_builds_unconfigured_provider_for_vault(monkeypatch) -> None:
    monkeypatch.setenv("EITOHFORGE_AUTH_JWT_SECRET", "x" * 32)
    monkeypatch.setenv("EITOHFORGE_SECRET_PROVIDER", "vault")
    monkeypatch.setenv("EITOHFORGE_SECRET_VAULT_URL", "http://vault:8200")
    monkeypatch.setenv("VAULT_TOKEN", "vault-token")
    settings = AppSettings()
    provider = build_secret_provider(settings)
    assert isinstance(provider, VaultSecretProvider)


def test_vault_secret_provider_get_parses_kv2_value(monkeypatch) -> None:
    from eitohforge_sdk.core import secrets as secrets_module

    provider = VaultSecretProvider(
        vault_url="http://vault:8200",
        vault_mount="secret",
        token="vault-token",
    )

    class FakeHTTPResponse:
        def __init__(self, body: str) -> None:
            self._body = body.encode("utf-8")

        def read(self) -> bytes:
            return self._body

        def __enter__(self) -> "FakeHTTPResponse":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

    expected_url = "http://vault:8200/v1/secret/data/mykey"

    def fake_urlopen(req, timeout: int = 5):  # noqa: ANN001
        assert req.full_url == expected_url
        token = req.headers.get("X-Vault-Token") or req.headers.get("X-vault-token")
        assert token == "vault-token"
        body = json.dumps({"data": {"data": {"value": "s3cr3t"}}})
        return FakeHTTPResponse(body)

    monkeypatch.setattr(secrets_module.urllib.request, "urlopen", fake_urlopen)

    assert provider.get("mykey") == "s3cr3t"

