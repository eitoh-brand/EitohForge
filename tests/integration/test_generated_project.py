import importlib
from pathlib import Path
import sys

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from eitohforge_cli.main import app


def test_generated_project_main_imports_and_exposes_health_route() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["create", "project", "my_service"])
        assert result.exit_code == 0
        crud_result = runner.invoke(app, ["create", "crud", "orders", "--path", "my_service"])
        assert crud_result.exit_code == 0
        assert (Path("my_service/tests/test_orders_crud.py")).exists()

        project_root = Path("my_service").resolve()
        pyproject = (project_root / "pyproject.toml").read_text(encoding="utf-8")
        middleware_py = (project_root / "app" / "core" / "middleware.py").read_text(encoding="utf-8")
        assert "eitohforge-sdk" in pyproject
        assert "from eitohforge_sdk.core import" in middleware_py
        sys.path.insert(0, str(project_root))
        try:
            main_module = importlib.import_module("app.main")
            config_module = importlib.import_module("app.core.config")
            auth_jwt_module = importlib.import_module("app.core.auth.jwt")
            auth_session_module = importlib.import_module("app.core.auth.session")
            auth_sso_module = importlib.import_module("app.core.auth.sso")
            auth_sso_adapters_module = importlib.import_module("app.core.auth.sso_adapters")
            abac_module = importlib.import_module("app.core.abac")
            security_module = importlib.import_module("app.core.security")
            security_context_module = importlib.import_module("app.core.security_context")
            audit_module = importlib.import_module("app.core.audit")
            health_core_module = importlib.import_module("app.core.health")
            capabilities_module = importlib.import_module("app.core.capabilities")
            feature_flags_module = importlib.import_module("app.core.feature_flags")
            security_hardening_module = importlib.import_module("app.core.security_hardening")
            idempotency_module = importlib.import_module("app.core.idempotency")
            rate_limit_module = importlib.import_module("app.core.rate_limit")
            request_signing_module = importlib.import_module("app.core.request_signing")
            observability_module = importlib.import_module("app.core.observability")
            tenant_module = importlib.import_module("app.core.tenant")
            plugins_module = importlib.import_module("app.core.plugins")
            versioning_module = importlib.import_module("app.core.versioning")
            secrets_module = importlib.import_module("app.core.secrets")
            error_registry_module = importlib.import_module("app.core.error_registry")
            error_middleware_module = importlib.import_module("app.core.error_middleware")
            validation_module = importlib.import_module("app.core.validation.engine")
            validation_hooks_module = importlib.import_module("app.core.validation.hooks")
            validation_rules_module = importlib.import_module("app.core.validation.rules")
            app_validation_service_module = importlib.import_module("app.application.services.validation")
            db_provider_module = importlib.import_module("app.infrastructure.database.provider")
            db_models_module = importlib.import_module("app.infrastructure.database.models")
            db_factory_module = importlib.import_module("app.infrastructure.database.factory")
            db_tx_module = importlib.import_module("app.infrastructure.database.transaction")
            cache_factory_module = importlib.import_module("app.infrastructure.cache.factory")
            cache_invalidation_module = importlib.import_module("app.infrastructure.cache.invalidation")
            cache_memory_module = importlib.import_module("app.infrastructure.cache.memory")
            cache_redis_module = importlib.import_module("app.infrastructure.cache.redis")
            storage_factory_module = importlib.import_module("app.infrastructure.storage.factory")
            storage_local_module = importlib.import_module("app.infrastructure.storage.local")
            storage_policy_module = importlib.import_module("app.infrastructure.storage.policy")
            storage_s3_module = importlib.import_module("app.infrastructure.storage.s3")
            storage_cdn_module = importlib.import_module("app.infrastructure.storage.cdn")
            jobs_contracts_module = importlib.import_module("app.infrastructure.jobs.contracts")
            jobs_memory_module = importlib.import_module("app.infrastructure.jobs.memory")
            messaging_contracts_module = importlib.import_module("app.infrastructure.messaging.contracts")
            messaging_dispatcher_module = importlib.import_module("app.infrastructure.messaging.dispatcher")
            notifications_contracts_module = importlib.import_module("app.infrastructure.notifications.contracts")
            notifications_gateway_module = importlib.import_module("app.infrastructure.notifications.gateway")
            notifications_templates_module = importlib.import_module(
                "app.infrastructure.notifications.template_engine"
            )
            external_api_contracts_module = importlib.import_module("app.infrastructure.external_api.contracts")
            external_api_client_module = importlib.import_module("app.infrastructure.external_api.client")
            search_contracts_module = importlib.import_module("app.infrastructure.search.contracts")
            search_memory_module = importlib.import_module("app.infrastructure.search.memory")
            search_opensearch_module = importlib.import_module("app.infrastructure.search.opensearch")
            search_factory_module = importlib.import_module("app.infrastructure.search.factory")
            sockets_contracts_module = importlib.import_module("app.infrastructure.sockets.contracts")
            sockets_auth_module = importlib.import_module("app.infrastructure.sockets.auth")
            sockets_hub_module = importlib.import_module("app.infrastructure.sockets.hub")
            webhooks_contracts_module = importlib.import_module("app.infrastructure.webhooks.contracts")
            webhooks_dispatcher_module = importlib.import_module("app.infrastructure.webhooks.dispatcher")
            webhooks_signing_module = importlib.import_module("app.infrastructure.webhooks.signing")
            saga_module = importlib.import_module("app.infrastructure.transactions.saga")
            repository_contracts_module = importlib.import_module("app.domain.repositories.contracts")
            value_objects_module = importlib.import_module("app.domain.value_objects")
            dto_module = importlib.import_module("app.application.dto.repository")
            error_dto_module = importlib.import_module("app.application.dto.error")
            response_dto_module = importlib.import_module("app.application.dto.response")
            crud_router_module = importlib.import_module("app.modules.orders.router")
            route_paths = {route.path for route in main_module.app.routes}
            assert "/health" in route_paths
            assert "/ready" in route_paths
            assert "/status" in route_paths
            assert "/sdk/capabilities" in route_paths
            assert "/sdk/feature-flags" in route_paths
            assert "/v1/health" in route_paths
            assert "/v1/admin/ping" in route_paths
            assert "/v1/tenant/{resource_tenant_id}/ping" in route_paths
            assert "/v2/health" in route_paths
            settings = config_module.AppSettings()
            assert settings.cache.provider == "redis"
            assert settings.storage.provider == "local"
            provider = secrets_module.build_secret_provider(settings)
            assert provider is not None
            postgres_provider = db_provider_module.PostgresProvider(settings=settings.database)
            assert settings.database.name in postgres_provider.dsn()
            assert db_models_module.Base is not None
            env_py = (project_root / "migrations" / "env.py").read_text(encoding="utf-8")
            assert "def run_migrations_online() -> None:" in env_py
            registry = db_factory_module.build_database_registry(settings)
            assert registry.has("primary")
            assert hasattr(repository_contracts_module, "RepositoryContract")
            assert hasattr(value_objects_module, "EmailAddress")
            assert dto_module.QuerySpec().pagination.page_size == 50
            assert hasattr(error_dto_module, "ApiErrorResponse")
            assert hasattr(response_dto_module, "ApiResponse")
            assert hasattr(crud_router_module, "router")
            assert hasattr(db_tx_module, "TransactionManager")
            assert hasattr(cache_factory_module, "build_cache_provider")
            assert hasattr(cache_invalidation_module, "AdvancedCacheProvider")
            assert hasattr(cache_memory_module, "MemoryCacheProvider")
            assert hasattr(cache_redis_module, "RedisCacheProvider")
            assert hasattr(storage_factory_module, "build_storage_provider")
            assert hasattr(storage_local_module, "LocalStorageProvider")
            assert hasattr(storage_policy_module, "StoragePolicyEngine")
            assert hasattr(storage_s3_module, "S3StorageProvider")
            assert hasattr(storage_cdn_module, "build_storage_public_url")
            assert hasattr(jobs_contracts_module, "BackgroundJobQueue")
            assert hasattr(jobs_memory_module, "InMemoryBackgroundJobQueue")
            assert hasattr(messaging_contracts_module, "EventBus")
            assert hasattr(messaging_dispatcher_module, "InMemoryEventBus")
            assert hasattr(notifications_contracts_module, "NotificationGateway")
            assert hasattr(notifications_gateway_module, "InMemoryNotificationGateway")
            assert hasattr(notifications_templates_module, "send_template")
            assert hasattr(external_api_contracts_module, "ExternalApiTransport")
            assert hasattr(external_api_client_module, "ResilientExternalApiClient")
            assert hasattr(search_contracts_module, "SearchProvider")
            assert hasattr(search_memory_module, "InMemorySearchProvider")
            assert hasattr(search_opensearch_module, "OpenSearchProvider")
            assert hasattr(search_factory_module, "build_search_provider")
            assert hasattr(sockets_contracts_module, "SocketPrincipal")
            assert hasattr(sockets_auth_module, "JwtSocketAuthenticator")
            assert hasattr(sockets_hub_module, "InMemorySocketHub")
            assert hasattr(webhooks_contracts_module, "WebhookTransport")
            assert hasattr(webhooks_dispatcher_module, "WebhookDispatcher")
            assert hasattr(webhooks_signing_module, "compute_webhook_signature")
            assert hasattr(saga_module, "SagaOrchestrator")
            assert hasattr(error_registry_module, "ErrorRegistry")
            assert hasattr(error_middleware_module, "register_error_handlers")
            assert hasattr(auth_jwt_module, "JwtTokenManager")
            assert hasattr(auth_session_module, "SessionManager")
            assert hasattr(auth_sso_module, "SsoBroker")
            assert hasattr(auth_sso_adapters_module, "OidcSsoProvider")
            assert hasattr(auth_sso_adapters_module, "SamlSsoProvider")
            assert hasattr(abac_module, "require_policies")
            assert hasattr(security_module, "require_roles")
            assert hasattr(security_context_module, "SecurityContext")
            assert hasattr(audit_module, "register_audit_middleware")
            assert hasattr(health_core_module, "get_status_payload")
            assert hasattr(capabilities_module, "register_capabilities_endpoint")
            assert hasattr(feature_flags_module, "register_feature_flags_endpoint")
            assert hasattr(security_hardening_module, "register_security_hardening_middleware")
            assert hasattr(idempotency_module, "register_idempotency_middleware")
            assert hasattr(rate_limit_module, "register_rate_limiter_middleware")
            assert hasattr(request_signing_module, "register_request_signing_middleware")
            assert hasattr(observability_module, "register_observability_middleware")
            assert hasattr(tenant_module, "register_tenant_context_middleware")
            assert hasattr(plugins_module, "PluginRegistry")
            assert hasattr(versioning_module, "register_versioned_routers")
            assert hasattr(validation_module, "ValidationEngine")
            assert hasattr(validation_hooks_module, "PermissionSecurityHook")
            assert hasattr(validation_rules_module, "PydanticSchemaRule")
            assert hasattr(app_validation_service_module, "ServiceValidationHooks")

            client = TestClient(main_module.app)
            ready_response = client.get("/ready")
            status_response = client.get("/status")
            assert ready_response.status_code == 200
            assert status_response.status_code == 200
            assert "status" in ready_response.json()
            assert "service" in status_response.json()
        finally:
            sys.path.pop(0)
            for module_name in list(sys.modules):
                if module_name == "app" or module_name.startswith("app."):
                    del sys.modules[module_name]

