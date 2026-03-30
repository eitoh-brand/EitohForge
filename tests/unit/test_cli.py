from pathlib import Path

from typer.testing import CliRunner

from eitohforge_cli.main import app


def test_version_command_returns_cli_version() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "eitohforge 0.1.0" in result.stdout


def test_create_project_generates_scaffold() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["create", "project", "my_service"])
        assert result.exit_code == 0
        assert "Project scaffold created at:" in result.stdout
        assert "(mode=sdk)" in result.stdout
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
        assert "(mode=standalone)" in result.stdout
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

