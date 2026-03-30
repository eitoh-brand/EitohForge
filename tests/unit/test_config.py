from pydantic import ValidationError

from eitohforge_sdk.core.config import AppSettings, AuthSettings, RealtimeSettings


def test_database_sqlalchemy_url_sqlite_memory() -> None:
    settings = AppSettings()
    settings.database.driver = "sqlite"
    settings.database.name = ":memory:"
    assert settings.database.sqlalchemy_url == "sqlite+pysqlite:///:memory:"


def test_database_sqlalchemy_url_sqlite_file(tmp_path) -> None:
    settings = AppSettings()
    dbfile = tmp_path / "app.db"
    settings.database.driver = "sqlite+pysqlite"
    settings.database.name = str(dbfile)
    assert "sqlite+pysqlite:///" in settings.database.sqlalchemy_url
    assert dbfile.resolve().as_posix() in settings.database.sqlalchemy_url


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


def test_settings_reject_realtime_jwt_when_jwt_disabled() -> None:
    try:
        AppSettings(
            auth=AuthSettings(jwt_enabled=False, jwt_secret="x" * 32),
            realtime=RealtimeSettings(enabled=True, require_access_jwt=True),
        )
        raise AssertionError("Expected validation failure when realtime requires JWT but auth JWT is off.")
    except ValidationError:
        pass


def test_settings_reject_wildcard_cors_in_prod(monkeypatch) -> None:
    monkeypatch.setenv("EITOHFORGE_AUTH_JWT_SECRET", "x" * 32)
    monkeypatch.setenv("EITOHFORGE_APP_ENV", "prod")
    monkeypatch.setenv("EITOHFORGE_RUNTIME_CORS_ALLOW_ORIGINS", "*")
    try:
        AppSettings()
        raise AssertionError("Expected wildcard CORS to be rejected in prod.")
    except ValidationError:
        pass

