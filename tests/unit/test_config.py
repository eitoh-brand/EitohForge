from pydantic import ValidationError

from eitohforge_sdk.core.config import AppSettings


def test_settings_load_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("EITOHFORGE_AUTH_JWT_SECRET", "x" * 32)
    monkeypatch.setenv("EITOHFORGE_DB_HOST", "db.internal")
    settings = AppSettings()
    assert settings.auth.jwt_secret == "x" * 32
    assert settings.database.host == "db.internal"


def test_settings_environment_precedence(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "EITOHFORGE_AUTH_JWT_SECRET=" + ("a" * 32) + "\n"
        "EITOHFORGE_DB_HOST=from-dot-env\n"
        "EITOHFORGE_APP_ENV=dev\n",
        encoding="utf-8",
    )
    (tmp_path / ".env.local").write_text(
        "EITOHFORGE_DB_HOST=from-dot-env-local\n"
        "EITOHFORGE_APP_ENV=staging\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("EITOHFORGE_DB_HOST", "from-process-env")
    settings = AppSettings()
    assert settings.database.host == "from-process-env"
    assert settings.app_env == "staging"


def test_settings_fail_fast_for_non_local_with_placeholder_secret(monkeypatch) -> None:
    monkeypatch.delenv("EITOHFORGE_AUTH_JWT_SECRET", raising=False)
    monkeypatch.setenv("EITOHFORGE_APP_ENV", "prod")
    try:
        AppSettings()
        raise AssertionError("Expected validation to fail for placeholder JWT secret in prod.")
    except ValidationError:
        pass

