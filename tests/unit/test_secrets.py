import pytest

from eitohforge_sdk.core.config import AppSettings
from eitohforge_sdk.core.secret_factory import build_secret_provider
from eitohforge_sdk.core.secrets import (
    DictSecretProvider,
    EnvSecretProvider,
    SecretNotFoundError,
    UnconfiguredSecretProvider,
    require_secret,
)


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


def test_secret_factory_builds_unconfigured_provider_for_vault(monkeypatch) -> None:
    monkeypatch.setenv("EITOHFORGE_AUTH_JWT_SECRET", "x" * 32)
    monkeypatch.setenv("EITOHFORGE_SECRET_PROVIDER", "vault")
    settings = AppSettings()
    provider = build_secret_provider(settings)
    assert isinstance(provider, UnconfiguredSecretProvider)

