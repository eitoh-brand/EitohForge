# EitohForge

EitohForge is an enterprise backend toolkit for Python/FastAPI that ships as one PyPI package:

- **SDK**: `eitohforge_sdk` (middleware, auth, tenanting, observability, infra contracts/adapters)
- **CLI**: `eitohforge` (project scaffolding, CRUD module generation, migration helpers, local multi-service dev)

This README is intentionally **long-form for PyPI** and covers features, module usage, and integration options.

---

## Gist (1 minute)

- Install: `pip install eitohforge` (or `pipx install eitohforge` for CLI isolation)
- Scaffold: `eitohforge create project my_service`
- Run generated app: `uvicorn app.main:app --reload`
- Discover runtime contracts: `GET /sdk/capabilities`
- Core stack: auth (JWT/session/SSO), rate limit, idempotency, request signing, audit, tenant isolation, observability, realtime, storage/cache/search/webhooks/jobs/contracts

---

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [CLI Usage (complete)](#cli-usage-complete)
- [Feature Enable/Disable Strategy](#feature-enabledisable-strategy)
- [Multi-Port and Multi-Instance Patterns](#multi-port-and-multi-instance-patterns)
- [Database Selection and Connectivity](#database-selection-and-connectivity)
- [SDK Usage (complete)](#sdk-usage-complete)
- [Feature Coverage and Module-by-Module Usage](#feature-coverage-and-module-by-module-usage)
- [Third-Party Support Matrix](#third-party-support-matrix)
- [Configuration and Environment Variables](#configuration-and-environment-variables)
- [Examples](#examples)
- [Documentation (multi-page)](#documentation-multi-page)
- [License](#license)

---

## Installation

Requires **Python 3.12+**.

### Install from PyPI

```bash
python -m pip install eitohforge
```

### Install CLI with pipx

```bash
pipx install eitohforge
eitohforge --help
```

### Install with uv

```bash
uv tool install eitohforge
# or for an app project:
uv add eitohforge
```

### Verify

```bash
eitohforge version
python -c "import eitohforge_sdk; print('ok')"
```

### Development install from source

```bash
git clone https://github.com/eitoh-brand/EitohForge.git
cd EitohForge
uv sync --all-extras
uv run eitohforge --help
```

---

## Quick Start

### 1) Create a project

```bash
eitohforge create project my_service
cd my_service
```

Options:

- `--mode sdk|standalone`
  - `sdk` (default): generated app consumes `eitohforge_sdk`
  - `standalone`: self-contained generated core files
- `--profile standard|minimal`
  - `standard`: most platform features enabled by default
  - `minimal`: opt-in features via env vars

### 2) Add a CRUD module

```bash
eitohforge create crud orders --path .
```

### 3) Run app

```bash
uvicorn app.main:app --reload
```

### 4) Check endpoints

- `GET /health`
- `GET /ready`
- `GET /status`
- `GET /sdk/capabilities`

---

## CLI Usage (complete)

### `eitohforge --help`

Top-level command groups:

- `version`
- `create`
- `db`
- `dev`

Current CLI intentionally focuses on scaffolding and operations. Feature toggling itself is runtime/config driven
(`EITOHFORGE_*` env vars and optional `ForgePlatformToggles`), not a separate `enable/disable` CLI command.

### `eitohforge version`

Prints installed package version (from distribution metadata).

### `eitohforge create`

#### Create project

```bash
eitohforge create project my_service --path . --mode sdk --profile standard
```

#### Create CRUD module

```bash
eitohforge create crud orders --path ./my_service
```

### `eitohforge db`

Alembic helper commands for generated projects:

```bash
eitohforge db init --path .
eitohforge db migrate -m "add orders table" --path .
eitohforge db upgrade --revision head --path .
eitohforge db downgrade --revision -1 --path .
eitohforge db current --path .
```

### `eitohforge dev`

Runs multiple uvicorn services from `forge.dev.json`.

```bash
eitohforge dev --path .
eitohforge dev validate --path .
```

Example `forge.dev.json`:

```json
{
  "schema_version": 1,
  "default_host": "127.0.0.1",
  "services": [
    {
      "name": "api",
      "module": "app.main:app",
      "port": 8000
    },
    {
      "name": "worker-api",
      "module": "worker_app.main:app",
      "port": 8100,
      "working_directory": "."
    }
  ]
}
```

---

## Feature Enable/Disable Strategy

There are three practical layers:

1) **Profile at scaffold time** (`create project --profile standard|minimal`)  
- `standard`: starts with more platform behavior enabled by default
- `minimal`: conservative defaults and explicit opt-in

2) **Runtime flags via environment variables** (`EITOHFORGE_*`)  
Common examples:

```bash
EITOHFORGE_RATE_LIMIT_ENABLED=true
EITOHFORGE_IDEMPOTENCY_ENABLED=true
EITOHFORGE_REQUEST_SIGNING_ENABLED=false
EITOHFORGE_OBSERVABILITY_ENABLED=true
EITOHFORGE_OBSERVABILITY_ENABLE_PROMETHEUS=true
EITOHFORGE_OBSERVABILITY_OTEL_ENABLED=true
EITOHFORGE_REALTIME_ENABLED=true
EITOHFORGE_TENANT_ENABLED=true
```

3) **Code-level toggles for controlled rollout** (`ForgePlatformToggles`)  
Useful when you want deterministic app composition per deployment stage.

```python
from eitohforge_sdk.core import ForgeAppBuildConfig, ForgePlatformToggles, build_forge_app
from eitohforge_sdk.core.config import get_settings

toggles = ForgePlatformToggles(
    realtime_websocket=False,
    observability=True,
    feature_flags=True,
)

app = build_forge_app(
    build=ForgeAppBuildConfig(
        title="My Service",
        settings_provider=get_settings,
        toggles=toggles,
    )
)
```

---

## Multi-Port and Multi-Instance Patterns

### Local multi-port development

Use `eitohforge dev` with `forge.dev.json` to run several FastAPI services at once (different ports, optional
working directories and env overrides).

```bash
eitohforge dev validate --path .
eitohforge dev --path .
```

### Horizontal multi-instance deployment

EitohForge apps are stateless by design at the HTTP layer and can run as multiple instances behind a load balancer.
For shared behavior across instances:

- **Session/cache**: use Redis provider
- **Realtime socket fanout/direct messaging**: set `EITOHFORGE_REALTIME_REDIS_URL`
- **Idempotency/rate-limit/replay semantics**: prefer shared backing stores for strict cross-instance behavior

Example production launch styles:

```bash
# Single process dev-like
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Multi-worker single node
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

In clustered/container environments, run multiple pods/instances behind your ingress/LB and keep Redis/Postgres as
shared stateful services.

---

## Database Selection and Connectivity

DB selection is controlled by `EITOHFORGE_DB_DRIVER` + related settings.

### PostgreSQL (default path)

```bash
EITOHFORGE_DB_DRIVER=postgresql+psycopg
EITOHFORGE_DB_HOST=localhost
EITOHFORGE_DB_PORT=5432
EITOHFORGE_DB_USERNAME=postgres
EITOHFORGE_DB_PASSWORD=postgres
EITOHFORGE_DB_NAME=eitohforge
```

### MySQL

```bash
EITOHFORGE_DB_DRIVER=mysql+pymysql
EITOHFORGE_DB_HOST=localhost
EITOHFORGE_DB_PORT=3306
EITOHFORGE_DB_USERNAME=root
EITOHFORGE_DB_PASSWORD=secret
EITOHFORGE_DB_NAME=my_service
```

### SQLite

```bash
EITOHFORGE_DB_DRIVER=sqlite
EITOHFORGE_DB_NAME=./data/app.db
# or in-memory:
# EITOHFORGE_DB_NAME=:memory:
```

### Connectivity and migration workflow

```bash
eitohforge db init --path .
eitohforge db migrate -m "init schema" --path .
eitohforge db upgrade --path .
eitohforge db current --path .
```

For tenant-aware Postgres schema isolation:

```bash
EITOHFORGE_TENANT_ENABLED=true
EITOHFORGE_TENANT_DB_SCHEMA_ISOLATION_ENABLED=true
EITOHFORGE_TENANT_DB_SCHEMA_NAME_TEMPLATE={tenant_id}
```

---

## SDK Usage (complete)

The package name is `eitohforge`, but imports are from `eitohforge_sdk`.

### Minimal app

```python
from fastapi import FastAPI

from eitohforge_sdk.core.capabilities import register_capabilities_endpoint
from eitohforge_sdk.core.config import get_settings

def create_app() -> FastAPI:
    app = FastAPI(title="My Service")
    register_capabilities_endpoint(app, settings_provider=get_settings)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app

app = create_app()
```

### Full platform app

```python
from fastapi import FastAPI

from eitohforge_sdk.core import ForgeAppBuildConfig, build_forge_app
from eitohforge_sdk.core.config import get_settings

app: FastAPI = build_forge_app(
    build=ForgeAppBuildConfig(
        title="My Service",
        settings_provider=get_settings,
    )
)
```

---

## Feature Coverage and Module-by-Module Usage

This section focuses on practical usage for each major capability.

### 1) API capabilities endpoint

```python
from eitohforge_sdk.core.capabilities import register_capabilities_endpoint
register_capabilities_endpoint(app)
```

Runtime discovery payload includes:

- feature toggles (`rate_limit`, `request_signing`, `tenant_isolation`, `realtime_websocket`, ...)
- provider choices (`cache`, `storage`, `search`, `secrets`)
- headers and runtime contracts (e.g., request signing headers)

### 2) Authentication: JWT

```python
from datetime import timedelta

from eitohforge_sdk.core.auth import JwtTokenManager, TokenType

manager = JwtTokenManager(
    secret="a-very-long-secret-at-least-32-chars",
    access_ttl=timedelta(minutes=15),
    refresh_ttl=timedelta(days=7),
)

pair = manager.issue_token_pair(subject="user-123", tenant_id="tenant-a")
access_claims = manager.decode_and_validate(pair.access_token, expected_type=TokenType.ACCESS)
rotated = manager.rotate_refresh_token(pair.refresh_token)
```

### 3) Authentication: sessions (memory or Redis)

```python
from eitohforge_sdk.core.auth import SessionManager, build_session_store

store = build_session_store(provider="memory")
# store = build_session_store(provider="redis", redis_url="redis://localhost:6379/0")

sessions = SessionManager(store=store)
record = sessions.create_session(subject="user-123", tenant_id="tenant-a")
validated = sessions.validate_session(record.session_id)
sessions.revoke_session(record.session_id)
```

### 4) Authentication: SSO broker + adapters (OIDC/SAML)

```python
from eitohforge_sdk.core.auth import InMemorySsoLinkStore, SsoBroker

link_store = InMemorySsoLinkStore()
broker = SsoBroker(link_store=link_store)
# Register OidcSsoProvider / SamlSsoProvider and call broker.authenticate(...)
```

### 5) RBAC / ABAC / security context

```python
from eitohforge_sdk.core import require_roles, require_policies, TenantMatchPolicy

# Use `require_roles("admin")` as route dependency
# Use `require_policies(TenantMatchPolicy())` for tenant-aware policy checks
```

### 6) Tenant isolation and context

`TenantContext.current()` is available when tenant middleware is wired.

- tenant headers enforced by `TenantIsolationRule`
- cache keys and storage keys are tenant-prefixed when tenant enabled
- optional Postgres schema isolation via `search_path`

### 7) Realtime WebSocket (JWT + rooms + direct messaging)

```python
from eitohforge_sdk.infrastructure.sockets.realtime_router import build_realtime_router, attach_socket_hub
from eitohforge_sdk.core.config import get_settings

attach_socket_hub(app, settings_provider=get_settings)
app.include_router(build_realtime_router(settings_provider=get_settings))
```

Client message types include `ping`, `join`, `leave`, `broadcast`, and `direct`.

### 8) Request signing middleware

```python
from eitohforge_sdk.core.request_signing import RequestSigningRule, register_request_signing_middleware

register_request_signing_middleware(
    app,
    RequestSigningRule(enabled=True),
    resolve_secret=lambda key_id: "shared-secret" if key_id in (None, "", "default") else None,
)
```

This enforces tamper and replay protection (`timestamp`, `nonce`, signature over canonical payload).

### 9) Idempotency middleware

```python
from eitohforge_sdk.core.idempotency import IdempotencyRule, register_idempotency_middleware

register_idempotency_middleware(
    app,
    IdempotencyRule(header_name="idempotency-key", ttl_seconds=86400),
)
```

### 10) Rate limiting middleware

```python
from eitohforge_sdk.core.rate_limit import RateLimitRule, register_rate_limiter_middleware

register_rate_limiter_middleware(
    app,
    RateLimitRule(max_requests=120, window_seconds=60),
)
```

### 11) Observability (request logging, metrics, tracing)

```python
from eitohforge_sdk.core.observability import (
    ObservabilityRule,
    PrometheusMetricsSink,
    register_observability_middleware,
    register_prometheus_metrics_endpoint,
)

metrics_sink = PrometheusMetricsSink(namespace="eitohforge")
register_prometheus_metrics_endpoint(app, metrics_sink=metrics_sink, path="/metrics")
register_observability_middleware(app, ObservabilityRule(enabled=True), metrics_sink=metrics_sink)
```

OTEL is enabled through settings (`EITOHFORGE_OBSERVABILITY_OTEL_*`) in full app wiring.

### 12) Audit middleware

```python
from eitohforge_sdk.core.audit import AuditRule, register_audit_middleware

register_audit_middleware(app, AuditRule(enabled=True, methods=("POST", "PUT", "PATCH", "DELETE")))
```

### 13) Security hardening middleware

```python
from eitohforge_sdk.core.security_hardening import SecurityHardeningRule, register_security_hardening_middleware

register_security_hardening_middleware(
    app,
    SecurityHardeningRule(enabled=True, max_request_bytes=1_048_576),
)
```

### 14) Cache providers (memory / Redis)

```python
from eitohforge_sdk.core.config import get_settings
from eitohforge_sdk.infrastructure.cache import build_cache_provider

cache = build_cache_provider(get_settings())
cache.set("k", {"ok": True}, ttl_seconds=30)
value = cache.get("k")
```

### 15) Storage providers (local / S3)

```python
from eitohforge_sdk.core.config import get_settings
from eitohforge_sdk.infrastructure.storage import build_storage_provider

storage = build_storage_provider(get_settings())
obj = storage.put_bytes("docs/report.txt", b"hello", content_type="text/plain")
exists = storage.exists(obj.key)
```

Tenant-enabled mode wraps with tenant key prefix automatically.

### 16) Search providers (memory / OpenSearch / Elasticsearch)

```python
from eitohforge_sdk.core.config import get_settings
from eitohforge_sdk.infrastructure.search import build_search_provider

search = build_search_provider(get_settings())
# index/search operations depend on provider contract
```

### 17) External API client (retry + circuit breaker)

```python
from eitohforge_sdk.infrastructure.external_api import ApiRequest, HttpMethod, ResilientExternalApiClient

client = ResilientExternalApiClient()
request = ApiRequest(method=HttpMethod.GET, url="https://api.example.com/ping")
# await client.call(request, transport=my_transport)
```

### 18) Background jobs (in-memory queue)

```python
from eitohforge_sdk.infrastructure.jobs import InMemoryBackgroundJobQueue

queue = InMemoryBackgroundJobQueue()
queue.register_handler("send-email", lambda job: None)
queue.enqueue("send-email", payload={"to": "u@example.com"})
# await queue.run_all_available()
```

### 19) Notifications

```python
from eitohforge_sdk.infrastructure.notifications import (
    InMemoryNotificationGateway,
    NotificationChannel,
    NotificationMessage,
    success_result_for,
)

gateway = InMemoryNotificationGateway()
gateway.register_sender(NotificationChannel.EMAIL, lambda msg: success_result_for(msg))
# await gateway.send(NotificationMessage(...))
```

### 20) Webhooks (signed delivery + dead-letter)

```python
from datetime import UTC, datetime

from eitohforge_sdk.infrastructure.webhooks import WebhookDispatcher, WebhookEndpointConfig, WebhookEvent

dispatcher = WebhookDispatcher()
event = WebhookEvent(name="order.created", payload={"id": "o-1"}, occurred_at=datetime.now(UTC))
endpoint = WebhookEndpointConfig(url="https://example.com/webhooks", secret="whsec-test")
# await dispatcher.dispatch(event, endpoint, transport=my_transport)
```

### 21) Messaging / event bus

Use `InMemoryEventBus` and dispatcher patterns for domain events; optional Redis bridge support exists for cross-process publish.

### 22) Feature flags and plugins

```python
from eitohforge_sdk.core import FeatureFlagDefinition, FeatureFlagService, PluginRegistry

flags = FeatureFlagService()
flags.register(FeatureFlagDefinition(key="new_checkout", enabled=True, rollout_percentage=10))

plugins = PluginRegistry()
# plugins.register(my_plugin_module)
```

---

## Third-Party Support Matrix

The SDK is designed to work with these ecosystem components (directly or through provider adapters):

| Area | Supported / integrated |
|------|-------------------------|
| Web framework | FastAPI, Starlette |
| Settings/validation | pydantic, pydantic-settings |
| ORM/migrations | SQLAlchemy, Alembic |
| Databases | PostgreSQL (`psycopg`), MySQL (`pymysql`), SQLite |
| Cache/session/realtime fanout | Redis |
| Tracing/metrics | OpenTelemetry (`opentelemetry-api/sdk/exporter-otlp`), Prometheus (`prometheus-client`) |
| Search | OpenSearch / Elasticsearch compatible endpoints |
| CLI | Typer |
| Templating/scaffolding | Jinja2 |

Notes:

- Some providers are optional at runtime and activated by `EITOHFORGE_*` settings.
- Missing optional deps typically surface as clear runtime errors (e.g., Redis store without redis runtime).

---

## Configuration and Environment Variables

All runtime settings are namespaced with `EITOHFORGE_*`.

Major groups:

- `EITOHFORGE_APP_*`
- `EITOHFORGE_DB_*`, `EITOHFORGE_DB_ANALYTICS_*`, `EITOHFORGE_DB_SEARCH_*`
- `EITOHFORGE_CACHE_*`
- `EITOHFORGE_STORAGE_*`
- `EITOHFORGE_AUTH_*`
- `EITOHFORGE_TENANT_*`
- `EITOHFORGE_RATE_LIMIT_*`
- `EITOHFORGE_IDEMPOTENCY_*`
- `EITOHFORGE_REQUEST_SIGNING_*`
- `EITOHFORGE_OBSERVABILITY_*`
- `EITOHFORGE_AUDIT_*`
- `EITOHFORGE_SEARCH_*`
- `EITOHFORGE_REALTIME_*`
- `EITOHFORGE_SECRET_*`

For exhaustive keys and behavior, see:

- `docs/guides/usage-complete.md`
- generated project `.env.example`

---

## Examples

- `examples/example-minimal/` — minimal app with health + capabilities
- `examples/example-enterprise/` — full platform wiring using `build_forge_app`

---

## Documentation (multi-page)

Yes, multi-page docs are supported in this repository via `docs/guides/`.

Start here:

- `docs/README.md` (docs index)
- `docs/guides/usage-complete.md` (full usage reference)
- `docs/guides/cookbook.md` (recipes)
- `docs/guides/realtime-websocket.md`
- `docs/guides/query-spec-reference.md`
- `docs/guides/python-packaging-and-publishing.md`
- `secure_backend_sdk_architecture.md` (architecture + implementation map)

---

## License

Proprietary (see `pyproject.toml`).
