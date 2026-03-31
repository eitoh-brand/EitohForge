from importlib.metadata import version as pkg_version
from pathlib import Path

from typer.testing import CliRunner

from eitohforge_cli.main import app


def test_version_command_returns_cli_version() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert f"eitohforge {pkg_version('eitohforge')}" in result.stdout


def test_help_shows_extended_top_level_command_groups() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "create" in result.stdout
    assert "db" in result.stdout
    assert "dev" in result.stdout
    assert "config" in result.stdout
    assert "docs" in result.stdout
    assert "ops" in result.stdout
    assert "feature-flags" in result.stdout
    assert "doctor" in result.stdout


def test_config_env_template_outputs_profile_defaults() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["config", "env-template", "--profile", "staging"])
    assert result.exit_code == 0
    assert "EITOHFORGE_APP_ENV=staging" in result.stdout
    assert "EITOHFORGE_REQUEST_SIGNING_ENABLED=true" in result.stdout


def test_docs_path_returns_known_topic_location() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["docs", "path", "usage"])
    assert result.exit_code == 0
    assert "docs/guides/usage-complete.md" in result.stdout


def test_config_feature_set_writes_env_flag() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(
            app,
            ["config", "feature-set", "rate_limit", "--enabled", "true", "--env-file", ".env.test"],
        )
        assert result.exit_code == 0
        content = Path(".env.test").read_text(encoding="utf-8")
        assert "EITOHFORGE_RATE_LIMIT_ENABLED=true" in content


def test_create_project_generates_scaffold() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["create", "project", "my_service"])
        assert result.exit_code == 0
        assert "Project scaffold created at:" in result.stdout
        assert "mode=sdk" in result.stdout
        assert "profile=standard" in result.stdout
        assert Path("my_service/alembic.ini").exists()
        assert Path("my_service/migrations/env.py").exists()
        assert Path("my_service/app/infrastructure/database/registry.py").exists()
        pyproject = Path("my_service/pyproject.toml").read_text(encoding="utf-8")
        middleware = Path("my_service/app/core/middleware.py").read_text(encoding="utf-8")
        assert "eitohforge-sdk" in pyproject
        assert "from eitohforge_sdk.core import" in middleware


def test_create_project_standalone_mode_generates_self_contained_core() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["create", "project", "my_service", "--mode", "standalone"])
        assert result.exit_code == 0
        assert "mode=standalone" in result.stdout
        assert "profile=standard" in result.stdout
        pyproject = Path("my_service/pyproject.toml").read_text(encoding="utf-8")
        rate_limit = Path("my_service/app/core/rate_limit.py").read_text(encoding="utf-8")
        assert "eitohforge-sdk" not in pyproject
        assert "class RateLimitRule:" in rate_limit


def test_create_crud_generates_module_scaffold() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        project_result = runner.invoke(app, ["create", "project", "my_service"])
        assert project_result.exit_code == 0

        crud_result = runner.invoke(app, ["create", "crud", "orders", "--path", "my_service"])
        assert crud_result.exit_code == 0
        assert "CRUD module scaffold created at:" in crud_result.stdout
        assert Path("my_service/app/modules/orders/__init__.py").exists()
        assert Path("my_service/app/modules/orders/schema.py").exists()
        assert Path("my_service/app/modules/orders/service.py").exists()
        assert Path("my_service/app/modules/orders/router.py").exists()
        assert Path("my_service/tests/test_orders_crud.py").exists()
        router_content = Path("my_service/app/modules/orders/router.py").read_text(encoding="utf-8")
        service_content = Path("my_service/app/modules/orders/service.py").read_text(encoding="utf-8")
        generated_test_content = Path("my_service/tests/test_orders_crud.py").read_text(encoding="utf-8")
        assert "ApiResponse" in router_content
        assert "PaginatedApiResponse" in router_content
        assert "ServiceValidationHooks" in service_content
        assert "test_orders_service_crud_cycle" in generated_test_content


def test_create_provider_generates_stub() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["create", "project", "my_service"])
        assert result.exit_code == 0
        prov = runner.invoke(app, ["create", "provider", "email_sendgrid", "--path", "my_service"])
        assert prov.exit_code == 0
        target = Path("my_service/app/providers/email_sendgrid.py")
        assert target.exists()
        assert "configure" in target.read_text(encoding="utf-8")


def test_create_pseudocode_generates_guide_file() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["create", "project", "my_service"])
        assert result.exit_code == 0
        pseudo = runner.invoke(app, ["create", "pseudocode", "--path", "my_service"])
        assert pseudo.exit_code == 0
        target = Path("my_service/docs/pseudocode/architecture-pseudocode.md")
        assert target.exists()
        content = target.read_text(encoding="utf-8")
        assert "Run REST API with SDK standard profile" in content

