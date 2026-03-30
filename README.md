# EitohForge

Enterprise FastAPI backend **SDK** (`eitohforge_sdk`) plus **CLI** (`eitohforge`) for scaffolding, migrations, and local multi-service development. One PyPI package (`eitohforge`) ships both; generated apps configure behavior with **`EITOHFORGE_*`** environment variables.

---

## Gist (30 seconds)

| What | Details |
|------|---------|
| **Install** | `pip install eitohforge` or `pipx install eitohforge` (Python ≥ 3.12) |
| **SDK** | `from eitohforge_sdk.core import build_forge_app, ForgeAppBuildConfig` — wires middleware, health, `/sdk/capabilities`, optional realtime, observability, tenant, flags, etc. |
| **CLI** | `eitohforge create project|crud`, `eitohforge db …`, `eitohforge dev` (multi-app from `forge.dev.json`) |
| **Discover** | `GET /sdk/capabilities` and `GET /sdk/feature-flags` expose what is enabled and which headers/paths apply |
| **Deep docs** | Multi-page guides live under [`docs/guides/`](docs/guides/) — [`usage-complete.md`](docs/guides/usage-complete.md) is the full reference |

**Is “multipage” possible?** Yes — but not inside a single `README.md`. PyPI and GitHub each show **one** README as the main landing text. For **multi-page** documentation, use the repo’s [`docs/guides/`](docs/guides/) tree (this project already does), publish a **MkDocs** / **Sphinx** site from `docs/`, or use **GitHub Wiki**. This README is the **overview + examples + feature map**; the guides hold exhaustive detail.

---

## Table of contents

- [Installation](#installation)
- [Quick start](#quick-start)
- [Configuration model](#configuration-model)
- [SDK usage](#sdk-usage)
- [Platform features (reference)](#platform-features-reference)
- [CLI reference](#cli-reference)
- [Capability & feature discovery](#capability--feature-discovery)
- [Examples in this repo](#examples-in-this-repo)
- [Troubleshooting (pointers)](#troubleshooting-pointers)
- [Documentation map (multi-page)](#documentation-map-multi-page)
- [License](#license)

---

## Installation

Requires **Python 3.12+**.

```bash
python -m pip install eitohforge
```

Isolated CLI tool install:

```bash
pipx install eitohforge
```

With **uv**:

```bash
uv tool install eitohforge
# or add to a project:
uv add eitohforge
```

**Development** (from a git clone):

```bash
git clone https://github.com/eitoh-brand/EitohForge.git
cd EitohForge
uv sync --all-extras
uv run eitohforge --help
```

Verify:

```bash
eitohforge version
python -c "import eitohforge_sdk; print('sdk ok')"
```

---

## Quick start

### 1) Scaffold a project

```bash
eitohforge create project my_service --path .
cd my_service
```

- **`--profile standard`** (default): `.env.example` leans toward most platform features **on** (you still set secrets in real envs).
- **`--profile minimal`**: slimmer defaults; enable features via `EITOHFORGE_*` when needed ([`docs/guides/forge-profiles.md`](docs/guides/forge-profiles.md)).
- **`--mode standalone`**: copies SDK patterns into the repo (no runtime `eitohforge` dependency in `pyproject.toml`). **`--mode sdk`** (default): generated app depends on the published SDK.

### 2) Add a CRUD module (optional)

```bash
eitohforge create crud orders --path .
```

### 3) Run the API

```bash
uvicorn app.main:app --reload
```

Open **`GET /health`**, **`GET /sdk/capabilities`**.

### 4) Database migrations (when using SQLAlchemy + Alembic layout)

```bash
eitohforge db init
eitohforge db migrate -m "init schema"
eitohforge db upgrade
```

---

## Configuration model

- **Prefix:** all runtime settings use **`EITOHFORGE_*`** (see generated **`.env.example`** in a scaffolded project).
- **Layering:** `.env`, then `.env.local`, then process environment (`AppSettings` / `pydantic-settings`).
- **Production:** set `EITOHFORGE_APP_ENV` to `dev`, `staging`, or `prod` and supply real secrets (JWT, DB URLs, etc.).

Full tables and behavior: **[`docs/guides/usage-complete.md`](docs/guides/usage-complete.md)** (sections 3–6).

---

## SDK usage

The PyPI distribution name is **`eitohforge`**. Python imports use **`eitohforge_sdk`**.

### Minimal: capabilities + health

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

Runnable: [`examples/example-minimal/`](examples/example-minimal/).

### Full stack: `build_forge_app`

Wires middleware, security context, tenant, health family, optional realtime, observability, feature flags, rate limit, idempotency, etc., according to **`AppSettings`** and optional **`ForgePlatformToggles`**.

```python
from fastapi import FastAPI

from eitohforge_sdk.core import ForgeAppBuildConfig, build_forge_app
from eitohforge_sdk.core.config import get_settings

def create_app() -> FastAPI:
    return build_forge_app(
        build=ForgeAppBuildConfig(
            title="My Service",
            settings_provider=get_settings,
        )
    )

app = create_app()
```

Runnable: [`examples/example-enterprise/`](examples/example-enterprise/).

### Settings in code

```python
from eitohforge_sdk.core.config import get_settings

settings = get_settings()
print(settings.app_name, settings.app_env)
```

---

## Platform features (reference)

Below is a **feature map** with typical **env knobs** and **where to read more**. For exhaustive behavior (validators, headers, paths), use **[`usage-complete.md`](docs/guides/usage-complete.md)** and the cookbook.

### App, runtime, CORS, HTTPS

| Concern | Env / notes | Guide |
|--------|-------------|--------|
| App name, env, log level | `EITOHFORGE_APP_*` | [usage-complete §3](docs/guides/usage-complete.md) |
| CORS, bind defaults, public URL | `EITOHFORGE_RUNTIME_*` | [usage-complete](docs/guides/usage-complete.md) |
| HTTPS redirect | `EITOHFORGE_RUNTIME_ENFORCE_HTTPS_REDIRECT` | capabilities → `runtime` |

### API versioning & deprecation

| Concern | Env / notes | Guide |
|--------|-------------|--------|
| Versioned routes | `/v1`, `/v2` patterns in app | [cookbook](docs/guides/cookbook.md) |
| Deprecation headers for legacy `/v1` | `EITOHFORGE_API_VERSION_*` | [usage-complete](docs/guides/usage-complete.md) |

### Authentication & authorization

| Concern | Notes | Guide |
|--------|--------|--------|
| JWT | `JwtTokenManager`, `EITOHFORGE_AUTH_*` | [usage-complete §5](docs/guides/usage-complete.md) |
| Sessions | Redis-backed session manager | generated `app.core.auth` |
| RBAC | `require_roles`, headers `x-roles`, `x-actor-id` | [usage-complete](docs/guides/usage-complete.md) |
| ABAC | Policy engine, `require_policies` | [usage-complete](docs/guides/usage-complete.md) |
| SSO | `SsoBroker`, OIDC/SAML adapters | [usage-complete §5](docs/guides/usage-complete.md) |

### Multi-tenancy

| Concern | Env / notes | Guide |
|--------|-------------|--------|
| Tenant isolation rules | `EITOHFORGE_TENANT_*` | [usage-complete](docs/guides/usage-complete.md) |
| `TenantContext.current()` | Set by middleware when tenant enabled | capabilities → `tenant` |
| Cache key prefix | `TenantScopedCacheProvider` when tenant enabled | SDK `infrastructure/cache` |
| Storage key prefix | `TenantScopedStorageProvider` (incl. presigned URLs) | SDK `infrastructure/storage` |
| Postgres schema isolation | `EITOHFORGE_TENANT_DB_SCHEMA_ISOLATION_ENABLED`, `*_DB_SCHEMA_NAME_TEMPLATE` | [usage-complete](docs/guides/usage-complete.md) |

### Database & persistence

| Concern | Notes | Guide |
|--------|--------|--------|
| SQLAlchemy URL / drivers | `EITOHFORGE_DB_*` (Postgres, MySQL, SQLite) | [usage-complete](docs/guides/usage-complete.md) |
| Alembic | `migrations/`, `alembic.ini` | [usage-complete §4](docs/guides/usage-complete.md) |
| `SQLAlchemyRepository` | `QuerySpec` filters, pagination | [`query-spec-reference.md`](docs/guides/query-spec-reference.md) |

### Cache

| Concern | Env / notes |
|--------|-------------|
| Provider | `EITOHFORGE_CACHE_*` (memory vs Redis) |
| Tenant-scoped keys | When `EITOHFORGE_TENANT_ENABLED=true` |

### Storage

| Concern | Env / notes |
|--------|-------------|
| Local / S3-style | `EITOHFORGE_STORAGE_*` |
| Tenant-prefixed keys | With tenant enabled |

### Messaging & domain events

| Concern | Notes |
|--------|--------|
| In-process bus | `EventBus` / dispatcher patterns |
| Redis publish bridge | `EITOHFORGE_*` messaging/redis settings (see [usage-complete](docs/guides/usage-complete.md)) |

### Realtime (WebSocket)

| Concern | Env / notes |
|--------|-------------|
| Socket route | `/realtime/ws` when `EITOHFORGE_REALTIME_ENABLED=true` |
| Redis fan-out hub | `EITOHFORGE_REALTIME_REDIS_URL` (cluster-wide broadcast) |
| JWT on handshake | `require_access_jwt` in settings |

See [`docs/guides/realtime-websocket.md`](docs/guides/realtime-websocket.md).

### Observability

| Concern | Env / notes |
|--------|-------------|
| Request logging / metrics / tracing flags | `EITOHFORGE_OBSERVABILITY_*` |
| Prometheus | `enable_prometheus`, path `prometheus_metrics_path` |
| OpenTelemetry OTLP | `otel_otlp_http_endpoint`, service name |

### Secrets

| Provider | Env / notes |
|----------|-------------|
| Env | Default |
| HashiCorp Vault | `EITOHFORGE_SECRET_*` (see [usage-complete](docs/guides/usage-complete.md)) |
| Cloud providers | AWS / Azure secret providers (see settings) |

### API quality & security middleware

| Feature | Env / notes |
|---------|-------------|
| Idempotency | `EITOHFORGE_IDEMPOTENCY_*` |
| Rate limiting | `EITOHFORGE_RATE_LIMIT_*` |
| Request signing | `EITOHFORGE_REQUEST_SIGNING_*` |
| Audit logging | `EITOHFORGE_AUDIT_*` |
| Security hardening (size, hosts, headers) | `EITOHFORGE_SECURITY_HARDENING_*` |

### Plugins & feature flags

| Feature | Notes |
|---------|--------|
| `PluginRegistry` | Register modules; `apply` at startup |
| Feature flags API | `GET /sdk/feature-flags` when enabled |

### CRUD generator

CLI: `eitohforge create crud <name>` — generates module, router, service, tests under `app/modules/<name>/`.

### Jobs, notifications, search, webhooks, external APIs

Generated projects and the SDK include **contracts and factories** for background jobs, notifications, OpenSearch-style search, outbound webhooks, and typed HTTP clients. Enable and configure via **`EITOHFORGE_*`** for each subsystem (see **[`usage-complete.md`](docs/guides/usage-complete.md)** and **[`cookbook.md`](docs/guides/cookbook.md)** for recipes).

---

## CLI reference

```bash
eitohforge --help
```

| Command | Purpose |
|---------|---------|
| `eitohforge version` | Print installed distribution version |
| `eitohforge create project <name>` | New project scaffold (`--mode`, `--profile`, `--path`) |
| `eitohforge create crud <module>` | CRUD module inside existing generated project |
| `eitohforge db init|migrate|upgrade|downgrade|current` | Alembic helpers |
| `eitohforge dev` | Run `forge.dev.json` multi-service dev |
| `eitohforge dev validate` | Validate manifest without starting servers |

Examples:

```bash
eitohforge create project my_service --path . --profile standard
eitohforge create project my_service --mode standalone

cd my_service
eitohforge create crud orders --path .
eitohforge db migrate -m "add orders"
eitohforge db upgrade
```

---

## Capability & feature discovery

At runtime (when routes are registered):

- **`GET /sdk/capabilities`** — JSON profile: enabled features, provider names, header names, tenant/realtime/observability blocks, deployment hints, SDK feature catalog.
- **`GET /sdk/feature-flags`** — evaluated flags when the feature-flag endpoint is enabled.

Use these for **mobile/web clients** to adapt behavior without hardcoding.

---

## Examples in this repo

| Path | Description |
|------|-------------|
| [`examples/example-minimal/`](examples/example-minimal/) | Health + capabilities only |
| [`examples/example-enterprise/`](examples/example-enterprise/) | `build_forge_app`, flags, richer wiring |

Each example has its own `README.md` with run/test commands.

---

## Troubleshooting (pointers)

| Symptom | Where to look |
|---------|----------------|
| Startup / validation errors | `EITOHFORGE_APP_ENV`, JWT secret, DB URL |
| 403 on writes | Tenant middleware: `x-tenant-id` / `EITOHFORGE_TENANT_*` |
| 429 | Rate limit settings |
| 401 on signed routes | `EITOHFORGE_REQUEST_SIGNING_*` |
| DB connection | Driver, host, port, credentials |

Full table: [usage-complete §9](docs/guides/usage-complete.md).

---

## Documentation map (multi-page)

| Document | Content |
|----------|---------|
| **[`docs/guides/usage-complete.md`](docs/guides/usage-complete.md)** | End-to-end install, config, auth, tenant, DB, migrations, realtime, observability, deploy, troubleshooting |
| **[`docs/guides/cookbook.md`](docs/guides/cookbook.md)** | Recipes (tenant, plugins, flags, hardening, perf) |
| **[`docs/guides/query-spec-reference.md`](docs/guides/query-spec-reference.md)** | `QuerySpec` operators and repository behavior |
| **[`docs/guides/realtime-websocket.md`](docs/guides/realtime-websocket.md)** | WebSocket protocol, rooms, Redis |
| **[`docs/guides/forge-profiles.md`](docs/guides/forge-profiles.md)** | `standard` vs `minimal` profiles |
| **[`docs/guides/enterprise-readiness-checklist.md`](docs/guides/enterprise-readiness-checklist.md)** | Production readiness |
| **[`docs/README.md`](docs/README.md)** | Index of roadmap, standards, and guides |
| **[`secure_backend_sdk_architecture.md`](secure_backend_sdk_architecture.md)** | Architecture spec + implementation appendix |

---

## License

Proprietary — see `pyproject.toml` metadata.
