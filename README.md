# EitohForge

[![PyPI version](https://img.shields.io/pypi/v/eitohforge.svg)](https://pypi.org/project/eitohforge/)
[![Python versions](https://img.shields.io/pypi/pyversions/eitohforge.svg)](https://pypi.org/project/eitohforge/)
[![Build](https://github.com/eitoh-brand/EitohForge/actions/workflows/ci.yml/badge.svg)](https://github.com/eitoh-brand/EitohForge/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](https://github.com/eitoh-brand/EitohForge)

EitohForge is an enterprise backend toolkit for Python/FastAPI that ships as one PyPI package:

- **SDK**: `eitohforge_sdk` (middleware, auth, tenanting, observability, infra contracts/adapters)
- **CLI**: `eitohforge` (project scaffolding, CRUD module generation, migration helpers, local multi-service dev)

This README is intentionally **long-form for PyPI** and covers features, module usage, and integration options.

### How to read this README

- **Main sections** (through [Deployment Blueprints](#deployment-blueprints-end-to-end)) follow a single path: run the API → project layout → **feature toggling** (including REST/WebSocket effects) → data & environments → scaling & CLI reference → SDK depth → infra blueprints.
- **[Appendix](#appendix-full-feature--operations-reference)** inlines the same topics as `docs/guides/` for offline / single-file PyPI reading — **intentional**, not accidental duplication.
- Use the [table of contents](#table-of-contents) or [PyPI quick navigation](#pypi-quick-navigation) to jump; skip the appendix unless you want the full inlined reference.

---

## Gist (1 minute)

- Install: `pip install eitohforge` (or `pipx install eitohforge` for CLI isolation)
- Scaffold + run REST API: `eitohforge create project my_service` -> `uvicorn app.main:app --reload`
- Validate baseline routes: `GET /health`, `/ready`, `/status`, `/sdk/capabilities`; **interactive API docs (FastAPI)**: `/docs` (Swagger UI), `/redoc` (ReDoc), `GET /openapi.json` (OpenAPI schema)
- Enable platform layers via env (CLI shortcut: `eitohforge config feature-set <name> --enabled true|false --env-file .env`): **security_hardening**, **audit**, **observability**, **jwt**, **https_redirect**, **idempotency**, **rate_limit**, **request_signing**, **tenant**, **feature_flags** (HTTP endpoint), **realtime**, **realtime_jwt** (socket handshake), **multi_db_analytics**, **multi_db_search** — run `eitohforge config feature-list` for the full key → `EITOHFORGE_*` map
- Everything else is still **`EITOHFORGE_*`** (no separate CLI toggle yet): **cache**, **storage**, **search**, **secrets** (Vault/AWS/Azure), **webhooks**, **jobs**, **notifications**, **messaging** — see [Configuration and Environment Variables](#configuration-and-environment-variables) and [Feature Coverage](#feature-coverage-and-module-by-module-usage)
- Promote by stage: local/dev/staging/prod (UAT usually maps operationally to `staging`)
- Scale topology when ready: multi-port local apps (`eitohforge dev`), multi-instance deploys, optional multi-DB/realtime fanout

---


## Hello World (SDK in 30 seconds)

This is the smallest possible FastAPI app that uses `eitohforge_sdk` to expose `/sdk/capabilities` and health endpoints. Docs are FastAPI defaults: `/docs`, `/redoc`, `/openapi.json`.

```python
from fastapi import FastAPI

from eitohforge_sdk.core.capabilities import register_capabilities_endpoint
from eitohforge_sdk.core.config import get_settings
from eitohforge_sdk.core.health import register_health_endpoints


def create_app() -> FastAPI:
    app = FastAPI(title="hello-eitohforge")
    register_capabilities_endpoint(app, settings_provider=get_settings)
    register_health_endpoints(app, settings_provider=get_settings)
    return app


app = create_app()
```

Run:

```bash
uvicorn app:app --reload
```

Then open:

- `GET /health`, `/ready`, `/status`
- `/sdk/capabilities`
- `/docs`, `/redoc`, `/openapi.json`

---


## PyPI Quick Navigation

- **Step 1 — Run REST API (SDK standard)**: [Quick start](#quick-start)
- **Step 2 — Project layout**: [folders/files and why](#project-architecture-foldersfiles-and-why)
- **Step 3 — Feature toggling (env + code + what appears on the wire)**: [Feature enable/disable](#feature-enabledisable-strategy) — includes REST/WebSocket and middleware tables in the same section
- **Step 4 — Data & environments**: [Database](#database-selection-and-connectivity), [multi-environment](#multi-environment-usage-localdevstagingprod)
- **Step 5 — Scale & multi-app**: [multi-port / multi-instance](#multi-port-and-multi-instance-patterns)
- **CLI reference**: [all `eitohforge` commands](#cli-usage-complete)
- **Deployment blueprints**: [single node, HA, Kubernetes](#deployment-blueprints-end-to-end)
- **Full reference appendix**: [inline docs + architecture spec](#appendix-full-feature--operations-reference)
- **Realtime/WebSocket deep dive**: [auth modes + message contracts + scaling](#7-realtime-websocket-jwt--rooms--direct-messaging)

## Table of Contents

- [How to read this README](#how-to-read-this-readme)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Project Architecture (folders/files and why)](#project-architecture-foldersfiles-and-why)
- [Feature Enable/Disable Strategy](#feature-enabledisable-strategy) (includes REST/WebSocket vs toggles)
- [Database Selection and Connectivity](#database-selection-and-connectivity)
- [Multi-Environment Usage (local/dev/staging/prod)](#multi-environment-usage-localdevstagingprod)
- [Multi-Port and Multi-Instance Patterns](#multi-port-and-multi-instance-patterns)
- [CLI Usage (complete)](#cli-usage-complete)
- [SDK Usage (complete)](#sdk-usage-complete)
- [Feature Coverage and Module-by-Module Usage](#feature-coverage-and-module-by-module-usage)
- [Third-Party Support Matrix](#third-party-support-matrix)
- [Configuration and Environment Variables](#configuration-and-environment-variables)
- [Examples](#examples)
- [Deployment Blueprints (end-to-end)](#deployment-blueprints-end-to-end)
- [Roadmap (high-level)](#roadmap-high-level)
- [Platform primitives (ecosystem gaps)](#platform-primitives-ecosystem-gaps)
- [Appendix: Full Feature & Operations Reference](#appendix-full-feature--operations-reference)
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
- **OpenAPI / Swagger (FastAPI built-ins)** — not separate EitohForge toggles; enabled unless you turn them off on `FastAPI(...)`:
  - **`GET /docs`** — Swagger UI (try requests in the browser)
  - **`GET /redoc`** — ReDoc (alternate layout)
  - **`GET /openapi.json`** — machine-readable OpenAPI 3 schema (for codegen, gateways, CI)

In **production**, disable or protect public docs: pass `docs_url=None`, `redoc_url=None`, and/or `openapi_url=None` to `FastAPI(...)`, or put the app behind an ingress that blocks `/docs` unless authenticated.

---

## Project Architecture (folders/files and why)

This repo ships both a reusable SDK and an operator-focused CLI. The structure is intentionally split so runtime framework code, scaffold generation code, docs, and tests evolve independently.

### Root folders

| Path | Why it exists |
|------|----------------|
| `src/eitohforge_sdk/` | Runtime SDK used by generated apps: middleware, settings, infra contracts/adapters, realtime, observability, security layers. |
| `src/eitohforge_cli/` | CLI for scaffolding and operations (`create`, `db`, `dev`, plus helper groups). |
| `docs/guides/` | Multi-page operational docs (usage, profiles, websocket, runbook, cookbook). |
| `docs/releases/` | Human-readable release notes by version. |
| `examples/` | Working sample projects for minimal and enterprise patterns. |
| `tests/unit/` | Unit tests for SDK and CLI behavior. |
| `scripts/` | Project automation helpers (build/release/support scripts). |
| `dist/` | Built wheel/sdist artifacts (generated for release checks). |

### Core SDK package map (`src/eitohforge_sdk/`)

| Path | Why needed |
|------|------------|
| `core/config.py` | Typed `AppSettings` (`EITOHFORGE_*`) and environment behavior resolution. |
| `core/forge_application.py` | `build_forge_app(...)` composition root wiring middleware + routes from settings/toggles. |
| `core/forge_toggles.py` | Code-level per-layer overrides (`ForgePlatformToggles`) for deterministic composition. |
| `core/health.py` | `/health`, `/ready`, `/status` endpoints. |
| `core/capabilities.py` | `/sdk/capabilities` runtime contract and feature introspection output. |
| `core/feature_flags.py` | Feature-flag endpoint wiring and service abstractions. |
| `core/*` middleware modules | Cross-cutting concerns: auth, tenant, idempotency, rate limit, signing, observability, audit. |
| `infrastructure/repositories/sqlalchemy_repository.py` | Generic repository implementation on SQLAlchemy with query spec support. |
| `infrastructure/sockets/` | WebSocket transport (`/realtime/ws`), auth extraction, optional Redis fan-out bridge. |
| `infrastructure/*` (cache/storage/search/webhooks/jobs/...) | Provider adapters and integration primitives for platform capabilities. |

### CLI package map (`src/eitohforge_cli/`)

| Path | Why needed |
|------|------------|
| `main.py` | Typer root command registration and entrypoint. |
| `commands/create.py` | Project and CRUD scaffold generation. |
| `commands/db.py` | Alembic wrapper commands for migration workflows. |
| `commands/dev.py` | Multi-service local startup from `forge.dev.json`. |
| `commands/config.py` | Env group discovery and profile env template output. |
| `commands/docs.py` | Fast lookup of docs topics and canonical file paths. |
| `templates.py` + `template_parts/*.py` | Source-of-truth scaffold templates split by concern (core/security/storage/cache/etc.). |

### Why this split matters

- `eitohforge_sdk` can be versioned and consumed independently of scaffold templates.
- CLI scaffolding remains composable: template modules map directly to generated project areas.
- Docs and tests stay close to behavior and release notes, making upgrades auditable.

---

## Feature Enable/Disable Strategy

**One place for toggles:** environment flags and `ForgePlatformToggles` decide which **HTTP routes**, **WebSocket** endpoints, and **middleware** are active. The tables under [What toggling affects on the wire](#what-toggling-affects-on-the-wire-rest--websocket) are part of this same topic — not a separate “REST API chapter.”

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
EITOHFORGE_REALTIME_REQUIRE_ACCESS_JWT=true
EITOHFORGE_AUTH_JWT_ENABLED=true
EITOHFORGE_RUNTIME_ENFORCE_HTTPS_REDIRECT=true
EITOHFORGE_TENANT_ENABLED=true
EITOHFORGE_DB_ANALYTICS_ENABLED=true
EITOHFORGE_DB_SEARCH_ENABLED=true
```

For TLS certificate pinning: apply at API gateway/client transport layer (outside SDK runtime flags), then document rotation policy in your platform runbook.

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

### What toggling affects on the wire (REST & WebSocket)

`build_forge_app(ForgeAppBuildConfig(...))` registers platform routes and middleware. **`ForgeAppBuildConfig.wire_platform_middleware=False`** builds a minimal FastAPI app (CORS + optional HTTPS redirect only) — **no** health/capabilities/feature-flags/realtime routers and **no** platform middleware stack.

| Surface | Method / path | Primary controls | If disabled or not mounted |
|---------|----------------|------------------|----------------------------|
| Health | `GET /health`, `/ready`, `/status` | `wire_health_family`; `ForgePlatformToggles.health`; `settings`-driven layers for readiness | **404** on those paths |
| Capabilities | `GET /sdk/capabilities` | `wire_capabilities`; `toggles.capabilities` | **404** |
| Feature flags | `GET` + `EITOHFORGE_FEATURE_FLAGS_ENDPOINT_PATH` (default `/sdk/feature-flags`) | `EITOHFORGE_FEATURE_FLAGS_ENABLED`; `wire_feature_flags`; `toggles.feature_flags` | **404** (endpoint not registered when `FEATURE_FLAGS_ENABLED=false`) |
| Prometheus | `GET` + `EITOHFORGE_OBSERVABILITY_PROMETHEUS_METRICS_PATH` (default `/metrics`) | `EITOHFORGE_OBSERVABILITY_ENABLED`; `EITOHFORGE_OBSERVABILITY_ENABLE_PROMETHEUS`; `toggles.observability` | **404** |
| Realtime | `WebSocket /realtime/ws` | `EITOHFORGE_REALTIME_ENABLED`; `wire_realtime_websocket`; `toggles.realtime_websocket`; Redis URL for cross-worker fan-out | **404** or failed upgrade; hub features off when `REALTIME_ENABLED=false` |

`/sdk/capabilities` JSON includes pointers such as `feature_flags.endpoint_path` so clients can discover the exact feature-flag URL.

### OpenAPI / Swagger UI (interactive HTTP docs)

These come from **FastAPI** on the generated `app` object (defaults apply unless you override `FastAPI(...)`):

| Path | Purpose |
|------|---------|
| `GET /docs` | Swagger UI — interactive “try it” browser for REST routes |
| `GET /redoc` | ReDoc — alternate API reference UI |
| `GET /openapi.json` | OpenAPI 3 schema (SDK clients, codegen, API gateways) |

They are **not** controlled by `EITOHFORGE_*` unless your `app.main` passes custom `docs_url` / `redoc_url` / `openapi_url`. For production hardening, disable or restrict these paths (see [Quick start — check endpoints](#4-check-endpoints)).

`eitohforge ops check` also probes `GET /openapi.json` to confirm the schema is served.

### Middleware-only toggles (HTTP outcomes)

These layers are toggled the same way as above (`EITOHFORGE_*` + optional `ForgePlatformToggles`); they do **not** add separate “feature CRUD” routes — they change behavior on matching requests:

| Layer | Key settings | Typical client-visible outcome |
|-------|----------------|--------------------------------|
| Security hardening | `EITOHFORGE_SECURITY_HARDENING_*` | **400** (body/hosts) / rejected requests |
| Request signing | `EITOHFORGE_REQUEST_SIGNING_*` (headers configurable) | **401** / **403** when signature invalid or missing |
| Rate limit | `EITOHFORGE_RATE_LIMIT_*` | **429** when exceeded |
| Idempotency | `EITOHFORGE_IDEMPOTENCY_*` + idempotency header (default `Idempotency-Key`) | **Replay**: same stored **status + body** + `X-Idempotent-Replay: true`; **409** if the same key is reused with a different payload |
| Tenant isolation | `EITOHFORGE_TENANT_*` | **400** / **403** when tenant missing or not allowed |
| Audit | `EITOHFORGE_AUDIT_*` | No dedicated status; writes audit records |
| Observability | `EITOHFORGE_OBSERVABILITY_*` | Request IDs / tracing headers per config; no error by default |

`ForgePlatformToggles` fields (`security_hardening`, `audit`, `observability`, …) override `AppSettings.*.enabled` per layer when you need code-level on/off regardless of env files.

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

## Multi-Environment Usage (local/dev/staging/prod)

`EITOHFORGE_APP_ENV` controls environment posture and capability hints (`local`, `dev`, `staging`, `prod`).

### Recommended environment layering

- Local laptop: `.env` + optional `.env.local`
- CI/dev namespace: CI/CD injected env vars
- Staging/prod: secret manager + deployment manifests (no plaintext secrets in repo)

### Example: local

```bash
EITOHFORGE_APP_ENV=local
EITOHFORGE_DB_DRIVER=sqlite
EITOHFORGE_DB_NAME=:memory:
EITOHFORGE_AUTH_JWT_SECRET=replace-with-long-local-secret
EITOHFORGE_OBSERVABILITY_ENABLED=true
EITOHFORGE_REALTIME_ENABLED=false
```

### Example: dev/staging

```bash
EITOHFORGE_APP_ENV=staging
EITOHFORGE_DB_DRIVER=postgresql+psycopg
EITOHFORGE_DB_HOST=postgres.staging.internal
EITOHFORGE_DB_PORT=5432
EITOHFORGE_DB_USERNAME=svc_eitohforge
EITOHFORGE_DB_PASSWORD=***from-secret-store***
EITOHFORGE_DB_NAME=eitohforge_staging
EITOHFORGE_CACHE_PROVIDER=redis
EITOHFORGE_CACHE_REDIS_URL=redis://redis.staging.internal:6379/0
EITOHFORGE_REALTIME_ENABLED=true
EITOHFORGE_REALTIME_REDIS_URL=redis://redis.staging.internal:6379/2
EITOHFORGE_OBSERVABILITY_OTEL_ENABLED=true
EITOHFORGE_OBSERVABILITY_OTEL_OTLP_HTTP_ENDPOINT=http://otel-collector:4318/v1/traces
```

### Example: production

```bash
EITOHFORGE_APP_ENV=prod
EITOHFORGE_RUNTIME_ENFORCE_HTTPS_REDIRECT=true
EITOHFORGE_SECURITY_HARDENING_ENABLED=true
EITOHFORGE_RATE_LIMIT_ENABLED=true
EITOHFORGE_REQUEST_SIGNING_ENABLED=true
EITOHFORGE_TENANT_ENABLED=true
EITOHFORGE_OBSERVABILITY_ENABLE_PROMETHEUS=true
```

### Environment profile guidance

- `local`: fastest feedback, lightweight dependencies
- `dev`: integration behavior close to prod, relaxed blast radius
- `staging`: pre-prod with production-like data shape/traffic simulation
- `prod`: strict security, observability, controlled rollout and autoscaling

### New deployment targets (UAT, staging, custom)

Two different meanings of “new environment”:

| What you want | Code change? | What to do |
|---------------|--------------|------------|
| **New operational target** (e.g. a UAT cluster, namespace, or CI stage) | **No** | Provision infra + secrets; set `EITOHFORGE_*` per target (often a dedicated secret store entry or `.env.uat`). Keep `EITOHFORGE_APP_ENV` as one of the **built-in** values: `local`, `dev`, `staging`, `prod`. Many teams map **UAT → `staging`** so posture stays “pre-prod-like” without a new enum. |
| **New first-class label** (e.g. `EITOHFORGE_APP_ENV=uat` as its own value) | **Yes** | Extend `app_env` in `AppSettings` (and generated templates), update `resolve_environment_behavior()` and any validators that branch on `app_env`. This is a small SDK/template change — not something you can turn on from env alone. |

**Practical recipe (no code change):** create `uat` (or any name) as a **deployment name** in K8s/Helm/CI; wire its ConfigMap/secret to `EITOHFORGE_APP_ENV=staging` (or `dev`) and set DB/cache URLs for that cluster. The **runtime** only sees the four built-in env values.

See also `docs/guides/usage-complete.md` → **Environments (`EITOHFORGE_APP_ENV`)**.

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

## CLI Usage (complete)

### `eitohforge --help`

Top-level command groups:

- `version`
- `create`
- `db`
- `dev`
- `config`
- `docs`
- `ops`
- `feature-flags`
- `doctor`

Use `eitohforge config feature-set` to write `EITOHFORGE_*` flags into an env file; that complements the [Feature Enable/Disable Strategy](#feature-enabledisable-strategy) section above.

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

#### Generate implementation pseudocode

```bash
eitohforge create pseudocode --path ./my_service
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

### `eitohforge config`

Configuration helpers for environment management:

```bash
eitohforge config env-groups
eitohforge config env-template --profile local
eitohforge config env-template --profile staging
eitohforge config feature-list
eitohforge config feature-set jwt --enabled true --env-file .env
eitohforge config feature-set realtime --enabled true --env-file .env
eitohforge config feature-set realtime_jwt --enabled true --env-file .env
eitohforge config feature-set https_redirect --enabled true --env-file .env
eitohforge config feature-set multi_db_analytics --enabled true --env-file .env
eitohforge config feature-set rate_limit --enabled true --env-file .env
eitohforge config feature-set request_signing --enabled false --env-file .env
```

### `eitohforge docs`

Documentation discovery helpers:

```bash
eitohforge docs list
eitohforge docs path usage
eitohforge docs path architecture
```

### `eitohforge ops`

Runtime endpoint checks against a deployed or local service:

```bash
eitohforge ops check --base-url http://127.0.0.1:8000
eitohforge ops smoke --base-url http://127.0.0.1:8000 --max-latency-ms 500
```

Checks `GET /health`, `/ready`, `/status`, `/sdk/capabilities`, and `GET /openapi.json` (prints a one-line OpenAPI summary; use `/docs` and `/redoc` in the browser for interactive docs).

### `eitohforge feature-flags`

Inspect the running feature flags endpoint:

```bash
eitohforge feature-flags get --base-url http://127.0.0.1:8000
# custom path:
eitohforge feature-flags get --base-url https://api.example.com --path /sdk/feature-flags
```

### `eitohforge doctor`

Sanity-check generated project structure:

```bash
eitohforge doctor check --path .
eitohforge doctor check --path . --file forge.dev.json
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

#### Socket authentication modes

- `EITOHFORGE_REALTIME_REQUIRE_ACCESS_JWT=true`:
  - token required at handshake
  - invalid/missing token is rejected with close code `1008`
- `false`:
  - anonymous principal is allowed
  - if token is present and valid, actor/tenant claims are still used

#### Client message contract (inbound)

```json
{ "type": "ping" }
{ "type": "join", "room": "orders:tenant-a" }
{ "type": "leave", "room": "orders:tenant-a" }
{ "type": "broadcast", "room": "orders:tenant-a", "event": "order.updated", "payload": { "id": "o-1" } }
{ "type": "direct", "target_actor_id": "user-42", "event": "notify", "payload": { "kind": "alert" } }
```

#### Server message contract (outbound examples)

```json
{ "type": "connected", "connection_id": "...", "actor_id": "user-1", "tenant_id": "tenant-a" }
{ "type": "joined", "room": "orders:tenant-a", "ok": true }
{ "type": "broadcast_result", "room": "orders:tenant-a", "delivered": 5 }
{ "type": "event", "event": "order.updated", "room": "orders:tenant-a", "payload": { "id": "o-1" } }
{ "type": "error", "code": "NOT_IN_ROOM", "message": "Join the room before broadcasting." }
```

#### Scaling sockets across instances

- Single-process: in-memory hub is sufficient
- Multi-worker / multi-pod: configure `EITOHFORGE_REALTIME_REDIS_URL` to enable Redis fanout hub
- Keep sticky sessions optional; fanout works across workers through Redis channel transport
- For private/direct actor messages across instances, ensure consistent actor identity in JWT claims

#### Production socket hardening checklist

- require JWT handshake (`EITOHFORGE_REALTIME_REQUIRE_ACCESS_JWT=true`)
- isolate room naming by tenant (`tenant_id` prefix convention)
- enforce payload size limits at ingress / reverse proxy
- monitor connection counts and broadcast delivery metrics
- apply backpressure/timeouts in client and gateway layers

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

## Deployment Blueprints (end-to-end)

These blueprints provide practical infrastructure layouts for common maturity stages.

### Blueprint A: Single node (small internal service)

Best for: development, POC, low traffic internal tools.

- 1 VM/container host running app (`uvicorn --workers N`)
- local or managed PostgreSQL
- optional Redis (if using Redis cache/session/realtime fanout)
- reverse proxy / TLS terminator (Nginx/Caddy/Ingress)

Suggested settings:

```bash
EITOHFORGE_APP_ENV=dev
EITOHFORGE_DB_DRIVER=postgresql+psycopg
EITOHFORGE_CACHE_PROVIDER=memory
EITOHFORGE_REALTIME_ENABLED=false
EITOHFORGE_OBSERVABILITY_ENABLE_PROMETHEUS=true
```

Trade-offs:

- simplest operations
- limited horizontal scale and fault tolerance

### Blueprint B: HA service (LB + app replicas + Redis + Postgres)

Best for: production baseline with predictable traffic and HA requirements.

Topology:

- L7 load balancer / ingress
- 2+ stateless app instances
- managed PostgreSQL (primary + replica/backup strategy)
- managed Redis (cache/session/realtime pub-sub)
- OTEL collector + Prometheus scraping (optional but recommended)

Suggested runtime contracts:

```bash
EITOHFORGE_APP_ENV=prod
EITOHFORGE_DB_DRIVER=postgresql+psycopg
EITOHFORGE_CACHE_PROVIDER=redis
EITOHFORGE_CACHE_REDIS_URL=redis://redis.internal:6379/0
EITOHFORGE_REALTIME_ENABLED=true
EITOHFORGE_REALTIME_REDIS_URL=redis://redis.internal:6379/2
EITOHFORGE_TENANT_ENABLED=true
EITOHFORGE_RATE_LIMIT_ENABLED=true
EITOHFORGE_REQUEST_SIGNING_ENABLED=true
```

Operational notes:

- keep app layer stateless
- use Redis-backed providers for cross-instance consistency
- perform zero-downtime deploys with rolling updates and readiness probes

### Blueprint C: Kubernetes (multi-env, autoscaling)

Best for: team-scale platform operations and multi-environment delivery.

Typical layout:

- namespace per environment (`dev`, `staging`, `prod`)
- Deployment for API app, optional Deployment for workers
- Service + Ingress for HTTP/WebSocket
- HPA for API pods
- Secret/ConfigMap for `EITOHFORGE_*`
- external managed Postgres/Redis/OpenSearch

Minimal K8s env strategy:

- `ConfigMap`: non-secret settings (feature flags, host/port, toggles)
- `Secret`: DB credentials, JWT/request-signing secrets, provider credentials
- rollout by image tag + env version stamp

### WebSocket and realtime in production blueprints

For Blueprint B/C:

- enable realtime route and JWT requirement:
  - `EITOHFORGE_REALTIME_ENABLED=true`
  - `EITOHFORGE_REALTIME_REQUIRE_ACCESS_JWT=true`
- configure Redis fanout:
  - `EITOHFORGE_REALTIME_REDIS_URL=redis://...`
- ensure ingress supports WebSocket upgrades and sane idle timeouts

### Database and migration operations in blueprints

Common release flow:

1. deploy new code with backward-compatible schema reads
2. run `eitohforge db upgrade` (or CI/CD migration step)
3. switch traffic progressively
4. monitor health/readiness/error/latency dashboards

For multi-tenant schema isolation in Postgres:

```bash
EITOHFORGE_TENANT_ENABLED=true
EITOHFORGE_TENANT_DB_SCHEMA_ISOLATION_ENABLED=true
EITOHFORGE_TENANT_DB_SCHEMA_NAME_TEMPLATE={tenant_id}
```

### Security baseline across all blueprints

- enforce HTTPS redirect and host hardening
- use strong JWT secret and rotate periodically
- enable request signing for write-critical APIs
- enable rate limit + idempotency on mutating routes
- avoid plaintext secrets in repo; use secret manager/CI secrets

---

## Platform primitives (ecosystem gaps)

These modules address common “framework maturity” gaps: contracts, persistence, providers, and inbound integrations.

| Area | What to use |
|------|-------------|
| **Repository contract** | `eitohforge_sdk.domain.BaseRepository` / `RepositoryContract` — `SQLAlchemyRepository` is the reference implementation. |
| **Response envelopes** | `eitohforge_sdk.application.dto.ok`, `paginated`, `err` — thin helpers over `ApiResponse` / `PaginatedApiResponse` / `ApiErrorResponse`. |
| **Feature flags + Redis** | `FeatureFlagDefinition.to_mapping` / `from_mapping`, `FeatureFlagService.reload`, `load_definitions_from_redis_json` / `save_definitions_to_redis_json`. |
| **Secrets** | `EITOHFORGE_SECRET_PROVIDER=env|vault|aws|azure` — Vault (`VaultSecretProvider`), AWS Secrets Manager (`pip install 'eitohforge[aws]'` + `boto3`), Azure Key Vault REST (`AZURE_KEY_VAULT_TOKEN` + `EITOHFORGE_SECRET_AZURE_VAULT_URL`). |
| **Inbound webhooks** | `register_inbound_webhook_router` — HMAC verification (timestamp-canonical or plain body digest). |
| **SendGrid email** | `build_sendgrid_email_sender` + `InMemoryNotificationGateway.register_sender("email", sender)`. |
| **Policy registry** | `PolicyRegistry` — register named `AccessPolicy` instances for composition and future DSL hooks. |
| **Multi-engine DB routing** | `EngineRegistry` — named SQLAlchemy engines; for logical roles + `DatabaseProvider`, see `infrastructure.database.registry.DatabaseRegistry`. |
| **CLI provider stub** | `eitohforge create provider <name> --path .` — scaffolds `app/providers/<name>.py`. |

---


## Appendix: Full Feature & Operations Reference

The section below inlines the repository’s multi-page guides and the architecture spec so PyPI visitors get a single, self-contained reference.

---

### Usage Complete (end-to-end reference)

## EitohForge — Complete Usage Guide

End-to-end reference for installing the SDK/CLI, configuring services, and operating generated applications.

### 1) Install

#### From source (development)

```bash
git clone https://github.com/eitoh-brand/EitohForge.git
cd EitohForge
uv pip install -e ".[dev]"
eitohforge --help
```

#### From an internal package index

```bash
pip install eitohforge
```

Verify:

```bash
eitohforge version
python -c "import eitohforge_sdk; print('ok')"
```

### 2) Create a project

**SDK-first (default)** — generated apps depend on `eitohforge` / `eitohforge-sdk` for core middleware and primitives:

```bash
eitohforge create project my_service
```

**Profile** — default `standard` (most platform features on in `.env.example`). Use `--profile minimal` for a slimmer default and enable features via env when needed (see `docs/guides/forge-profiles.md`).

**Standalone** — self-contained copies of SDK patterns inside the repo (no runtime SDK dependency):

```bash
eitohforge create project my_service --mode standalone
```

#### Add a CRUD module

```bash
cd my_service
eitohforge create crud orders --path .
```

### 3) Configuration

- All runtime settings use the `EITOHFORGE_*` prefix (see generated `.env.example`).
- Layered files: `.env`, then `.env.local`, then process environment (see `pydantic-settings` model config in `AppSettings`).
- **Production**: set `EITOHFORGE_APP_ENV` to `dev`, `staging`, or `prod` and supply a real `EITOHFORGE_AUTH_JWT_SECRET` (local allows the placeholder).

#### Environments (`EITOHFORGE_APP_ENV`)

**Built-in values** (validated in `AppSettings`): `local`, `dev`, `staging`, `prod`. Pick one per deployment; the capability profile’s `deployment` block reflects derived hints (see `resolve_environment_behavior` in the SDK).

**Operational “new environment”** (no code change): provision a new target (namespace, cluster stage, etc.) and give it its own secrets and env file or secret store — e.g. `.env.staging`, CI variables for `uat`, Helm values — still setting `EITOHFORGE_APP_ENV` to one of the built-in values. Many teams map **UAT** to `staging` so behavior stays “pre-production-like” without a separate enum.

**New named stage** (e.g. `uat` as its own label): today requires **extending** the `app_env` type in `AppSettings` (and the generated `app/core/config.py` template) plus updating `resolve_environment_behavior()` and any validators that branch on `app_env`. That is a small SDK/template change, not something toggled from env alone.

Key groups:

| Area | Prefix | Notes |
|------|--------|--------|
| App | `EITOHFORGE_APP_` | name, env, log level |
| Database | `EITOHFORGE_DB_` | SQLAlchemy URL pieces. **Postgres:** default `driver=postgresql+psycopg`. **MySQL:** `EITOHFORGE_DB_DRIVER=mysql+pymysql`, `EITOHFORGE_DB_PORT=3306` (typical), `name` = database name. **SQLite:** `EITOHFORGE_DB_DRIVER=sqlite` (or `sqlite+pysqlite`), `EITOHFORGE_DB_NAME=:memory:` or path to `.db` file. |
| API versioning | `EITOHFORGE_API_VERSION_` | `DEPRECATE_V1`, optional `V1_SUNSET_HTTP_DATE`, `V1_LINK_DEPRECATION` for `/v1` deprecation headers (see cookbook). |
| Realtime cluster | `EITOHFORGE_REALTIME_` | `REDIS_URL` enables cross-worker **broadcast** fan-out; optional `REDIS_BROADCAST_CHANNEL` (default `eitohforge:realtime:broadcast`). |
| Auth | `EITOHFORGE_AUTH_` | JWT secret, token TTL |
| Cache | `EITOHFORGE_CACHE_` | Redis vs memory |
| Tenant | `EITOHFORGE_TENANT_` | isolation rules (+ optional Postgres schema isolation via `EITOHFORGE_TENANT_DB_SCHEMA_ISOLATION_ENABLED` and `EITOHFORGE_TENANT_DB_SCHEMA_NAME_TEMPLATE`). |
| Feature flags | `EITOHFORGE_FEATURE_FLAGS_` | endpoint path, enable |
| Security hardening | `EITOHFORGE_SECURITY_HARDENING_` | hosts, max body, headers |
| Observability | `EITOHFORGE_OBSERVABILITY_` | request logging/metrics/tracing; optional Prometheus `/metrics` + OTEL OTLP traces. |
| Secret management | `EITOHFORGE_SECRET_` | secret provider selection (`env` / `vault` / `aws` / `azure`). Vault reads KV values on each `get` (no client-side caching), so rotations are picked up naturally; Vault token comes from `VAULT_TOKEN` (or `EITOHFORGE_SECRET_VAULT_TOKEN` fallback). |

Capability discovery for clients:

- `GET /sdk/capabilities` — enabled features and header names.
- `GET /sdk/feature-flags` — evaluated flags for the current request context.
- **WebSocket** — generated apps expose `/realtime/ws` when `EITOHFORGE_REALTIME_ENABLED=true` (JWT handshake, rooms, broadcast). See `docs/guides/realtime-websocket.md`.

### 4) Migrations (Alembic)

Generated projects include `migrations/` and `alembic.ini`.

```bash
cd my_service
eitohforge db init          # first-time
eitohforge db migrate -m "message"
eitohforge db upgrade
eitohforge db current
```

CI enforces migration policy via `scripts/check_migration_policy.py` (destructive changes require an explicit approval marker).

### 5) Authentication and authorization

- **JWT**: `JwtTokenManager` (access/refresh, rotation) — see `app.core.auth` in generated apps.
- **Sessions**: Redis-backed session manager with revocation hooks.
- **RBAC**: `require_roles` dependency from headers (`x-roles`, `x-actor-id`).
- **ABAC**: policy engine and `require_policies` for tenant-aware routes.
- **SSO**: `SsoBroker` with OIDC/SAML adapters (`OidcSsoProvider`, `SamlSsoProvider`).

### 6) Plugins and extension

- Implement a `PluginModule` (name + optional `register_routes` / `register_providers` / `register_events`).
- Register with `PluginRegistry` and call `apply(...)` during startup.

### 7) Deploy and operate

- **Health**: `GET /health`, `GET /ready`, `GET /status`.
- **Runbook**: `docs/guides/operations-runbook.md`.
- **TLS / LB / rollout**: `docs/guides/tls-and-cert-rotation-runbook.md`, `load-balancing-and-health-routing.md`, `deployment-strategies-and-rollback-controls.md`.

Container-style run (example):

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 8) Packaging and release

- Build: `python -m build` (reproducibility checks in CI).
- Publish: internal workflow `publish-internal.yml`; optional PyPI `publish-pypi.yml`.
- Details: `docs/guides/python-packaging-and-publishing.md`.

### 9) Troubleshooting

| Symptom | Check |
|---------|--------|
| Startup fails on config | Env vars and `AppSettings` validators (`EITOHFORGE_APP_ENV`, JWT secret). |
| 403 on writes | Tenant middleware: `x-tenant-id` / `EITOHFORGE_TENANT_*`. |
| 429 responses | Rate limit headers and `EITOHFORGE_RATE_LIMIT_*`. |
| 401 on signed APIs | Request signing secret and clock skew (`EITOHFORGE_REQUEST_SIGNING_*`). |
| DB connection errors | `EITOHFORGE_DB_*`, driver (`postgresql+psycopg`, `mysql+pymysql`, `sqlite`), port (3306 vs 5432), and network reachability. |
| Import errors in SDK mode | `pip install eitohforge` and matching version in generated `pyproject.toml`. |

### 10) Reference examples

- **Minimal**: `examples/example-minimal/` — capabilities + health.
- **Enterprise-style**: `examples/example-enterprise/` — hardening, observability, tenant, flags, health family.

See each example’s `README.md` for run and test commands.

### 11) Further reading

- `docs/guides/cookbook.md`
- `docs/guides/realtime-websocket.md`
- `docs/guides/forge-profiles.md` (includes `forge_platform_toggles_uniform`)
- `docs/guides/query-spec-reference.md` — `QuerySpec` operators and `SQLAlchemyRepository` behavior
- Repository root `secure_backend_sdk_architecture.md` — specification; see its appendix for implementation coverage vs §1–§44
- `docs/guides/enterprise-readiness-checklist.md`
- `docs/guides/testing-and-example-project-strategy.md`
- `docs/roadmap/architecture-coverage-matrix.md`

---

### Cookbook (recipes)

## EitohForge Cookbook

Practical recipes for common implementation patterns.

### 1) Enable Strict Tenant Isolation

Set:

- `EITOHFORGE_TENANT_ENABLED=true`
- `EITOHFORGE_TENANT_REQUIRED_FOR_WRITE_METHODS=true`
- `EITOHFORGE_TENANT_RESOURCE_TENANT_HEADER=x-resource-tenant-id`

Behavior:

- write methods without tenant context are denied (`403`)
- cross-tenant access via mismatched resource tenant header is denied (`403`)

### 2) Add a Plugin Module

Implement a plugin object with a unique `name`, optionally:

- `register_routes(app)`
- `register_providers(registry)`
- `register_events(registry)`

Register it with `PluginRegistry.register(plugin)` and apply with `PluginRegistry.apply(...)`.

### 3) Roll Out a Feature Gradually

Use `FeatureFlagService` and register:

- `FeatureFlagDefinition(key="new-ui", rollout_percentage=10)`

Then evaluate with actor/tenant context:

- `FeatureFlagTargetingContext(actor_id="actor-1", tenant_id="tenant-a")`

Expose runtime values via `register_feature_flags_endpoint(app)`.

### 4) Harden HTTP Surface

Use `register_security_hardening_middleware` with `SecurityHardeningRule` to:

- enforce max request size
- restrict allowed hosts
- set strict response security headers

### 5) Baseline and Check Performance

Generate baseline:

- `uv run python scripts/performance_baseline.py --mode baseline`

Run regression check:

- `uv run python scripts/performance_baseline.py --mode check --threshold 25`

### 6) Realtime WebSocket (generated apps)

- Ensure `EITOHFORGE_REALTIME_ENABLED=true` (default).
- Connect to `/realtime/ws` with a valid **access** JWT (`?token=...` or `Authorization: Bearer ...`).
- Use JSON frames: `join` / `leave` / `broadcast` / `direct` / `presence` / `ping` — see `docs/guides/realtime-websocket.md`.
- **Single worker:** default in-memory hub only.
- **Multi-worker (`EITOHFORGE_REALTIME_REDIS_URL`):** `RedisFanoutSocketHub` **PUBLISH**es each client **`broadcast`** and **`direct`** to peers; **`presence` / `room_members` stay per process**. Private “rooms” are a **naming convention** only; **`direct`** targets `actor_id` (JWT subject) and does **not** enforce authorization—see `realtime-websocket.md`.
- **Manual two-worker check:** run Redis; start two Uvicorn processes with the same `EITOHFORGE_REALTIME_REDIS_URL`; connect WebSockets on different workers, join the same room, broadcast from one — the other should receive the event. Expect each worker’s `presence` to list only its local connections.

### 7) Deprecate `/v1` with HTTP headers

`build_forge_app` registers deprecation middleware automatically. Enable with:

- `EITOHFORGE_API_VERSION_DEPRECATE_V1=true`
- Optional `EITOHFORGE_API_VERSION_V1_SUNSET_HTTP_DATE` (e.g. `Sat, 31 Dec 2026 23:59:59 GMT`)
- Optional `EITOHFORGE_API_VERSION_V1_LINK_DEPRECATION` (URL for `Link: <...>; rel="deprecation"`)

Responses for paths starting with `/v1` then include `Deprecation: true` plus `Sunset` / `Link` when set.

### 8) Versioned OpenAPI documents

FastAPI exposes one root OpenAPI by default. For **separate** OpenAPI per major version, mount sub-applications:

```python
from fastapi import FastAPI

root = FastAPI()
v1_app = FastAPI(title="API v1", openapi_url="/openapi.json")
v2_app = FastAPI(title="API v2", openapi_url="/openapi.json")
root.mount("/v1", v1_app)
root.mount("/v2", v2_app)
```

Clients then use `/v1/openapi.json` and `/v2/openapi.json`. Combine with `register_versioned_routers` on each sub-app or include routers manually.

### 9) Event bus: local + Redis publish

- In-process: `InMemoryEventBus` from `eitohforge_sdk.infrastructure.messaging`.
- Cross-process fan-out: `build_redis_publishing_event_bus(redis_url="redis://localhost:6379/0")` implements `EventBus`; `publish` notifies local subscribers and `PUBLISH`es JSON to `eitohforge:evt:{event_name}`.

Other workers must run a Redis `SUBSCRIBE` loop (or use a task queue) to consume those messages; the SDK does not start a background subscriber in the web process.

### 10) Observability: Prometheus + OTEL

#### Prometheus metrics (`/metrics`)

- Enable: `EITOHFORGE_OBSERVABILITY_ENABLE_PROMETHEUS=true`
- Path: `EITOHFORGE_OBSERVABILITY_PROMETHEUS_METRICS_PATH` (default: `/metrics`)

Request metrics are exported using a per-app Prometheus registry:

- `eitohforge_http_requests_total{method,path,status}`
- `eitohforge_http_requests_duration_ms{method,path,status}`

#### OTEL tracing

- Enable: `EITOHFORGE_OBSERVABILITY_OTEL_ENABLED=true`
- Service name: `EITOHFORGE_OBSERVABILITY_OTEL_SERVICE_NAME` (default: `eitohforge`)
- OTLP traces over HTTP (optional): `EITOHFORGE_OBSERVABILITY_OTEL_OTLP_HTTP_ENDPOINT`

When enabled, responses include `x-trace-id` (derived from the active OTEL span context when available).

---

### Forge Profiles

## Forge scaffold profiles and feature toggles

### CLI profiles (`create project`)

```bash
eitohforge create project my_api --profile standard   # default
eitohforge create project my_api --profile minimal      # most platform features off in `.env.example`
```

- **standard** — typical enterprise defaults (tenant, rate limit, observability, audit, realtime WebSocket, feature flags, etc. enabled in the generated `.env.example`).
- **minimal** — the same codebase layout, but `.env.example` starts with most optional middleware **disabled**. Turn features on by setting the matching `EITOHFORGE_*_ENABLED` (or related) variables to `true` and redeploying.

Runtime behavior always follows **loaded settings** (`AppSettings`), not the profile name, after you copy `.env.example` → `.env`.

### `build_forge_app` toggles (SDK)

For SDK-only apps, use **`ForgeAppBuildConfig.toggles`** (`ForgePlatformToggles`) to override each layer without changing environment:

- Each field is `True` | `False` | `None`.
- **`None`** means “use `AppSettings`” (e.g. `rate_limit.enabled`).
- **`False`** forces that layer off even if env says on; **`True`** forces it on.

```python
from eitohforge_sdk.core import ForgeAppBuildConfig, ForgePlatformToggles, build_forge_app

app = build_forge_app(
    build=ForgeAppBuildConfig(
        toggles=ForgePlatformToggles(
            rate_limit=False,
            realtime_websocket=False,
            https_redirect=False,
        ),
    )
)
```

Other toggle keys match platform concerns: `security_hardening`, `audit`, `observability`, `request_signing`, `idempotency`, `tenant`, `security_context`, `cors`, `health`, `capabilities`, `feature_flags`, `realtime_websocket`, `https_redirect`.

`wire_realtime_websocket=False` on **`ForgeAppBuildConfig`** skips mounting `/realtime/ws` entirely (in addition to toggles).

#### Uniform toggle (all layers on or off)

To force **every** `ForgePlatformToggles` field to the same value (overriding `AppSettings` for each wired layer), use:

```python
from eitohforge_sdk.core import ForgeAppBuildConfig, build_forge_app, forge_platform_toggles_uniform

app = build_forge_app(
    build=ForgeAppBuildConfig(
        toggles=forge_platform_toggles_uniform(enabled=False),
        wire_realtime_websocket=False,
    )
)
```

Use **`enabled=True`** only when you intentionally want all toggled layers on regardless of env. **`wire_*`** flags on `ForgeAppBuildConfig` are separate: set them explicitly if you need to skip router families entirely.

### Environment flags (auth, HTTPS, WebSocket)

| Concern | Variables |
|--------|-----------|
| JWT issuance/validation for HTTP and WS | `EITOHFORGE_AUTH_JWT_ENABLED` (default `true`) |
| WebSocket endpoint | `EITOHFORGE_REALTIME_ENABLED` |
| Require access JWT on `/realtime/ws` | `EITOHFORGE_REALTIME_REQUIRE_ACCESS_JWT` (if `true` and realtime on, `AUTH_JWT_ENABLED` must be `true`) |
| Redirect HTTP→HTTPS (app-level; TLS usually terminates at proxy) | `EITOHFORGE_RUNTIME_ENFORCE_HTTPS_REDIRECT` |
| CORS | `EITOHFORGE_RUNTIME_CORS_ALLOW_ORIGINS`, etc. |

`GET /sdk/capabilities` exposes `auth`, `runtime`, and `realtime` blocks for clients.

---

### Realtime WebSocket Guide

## Realtime WebSocket (`/realtime/ws`)

Generated apps register a **first-class** WebSocket endpoint when `EITOHFORGE_REALTIME_ENABLED=true` (default).

### Handshake

- **`EITOHFORGE_REALTIME_REQUIRE_ACCESS_JWT`** (default `true`): when `false`, connections are accepted without a token (anonymous `actor_id`); optional JWT still upgrades the principal when `EITOHFORGE_AUTH_JWT_ENABLED=true`.
- When `require_access_jwt` is `true`, a **JWT access token** is required before messages are accepted (and **`EITOHFORGE_AUTH_JWT_ENABLED`** must be `true`).
- Pass the token as query `?token=<access_jwt>` and/or `Authorization: Bearer <access_jwt>` (query wins if both are set — see `extract_socket_token`).

### Hub

When **`EITOHFORGE_REALTIME_REDIS_URL`** is unset, the hub is **`InMemorySocketHub`** on `app.state.socket_hub` (single process). When set, **`build_forge_app`** uses **`RedisFanoutSocketHub`**: **broadcast** and **direct** traffic fan out across workers via Redis; **presence** / **room membership** stay per process (see cookbook).

### Private channels vs direct messages

| Mechanism | What the SDK does | What your app must do |
|-----------|-------------------|------------------------|
| **Room “privacy”** | None — any client can `join` any room name string. | Encode tenancy or secrecy in **room naming** (e.g. `tenant:{id}:orders`) and enforce policy in HTTP APIs or custom middleware before exposing room names. |
| **`type: "direct"`** | Delivers to all WebSocket connections whose **`actor_id`** matches **`target_actor_id`** (JWT subject by default). Works across workers when Redis is enabled. **Does not** encrypt payloads or prove the recipient’s tenant; **authorization** (who may message whom) is **application-owned**. | Enforce ABAC/RBAC in services or reject sensitive `target_actor_id` values server-side if you add hooks later. |

**Not supported by the SDK:** end-to-end encryption, read receipts, or guaranteed offline delivery. Use app-level queues or push for those.

### Client JSON protocol (text frames)

| `type` | Fields | Server response |
|--------|--------|-----------------|
| `ping` | — | `{ "type": "pong" }` |
| `join` | `room` (string) | `{ "type": "joined", "room", "ok" }` |
| `leave` | `room` | `{ "type": "left", "room", "ok" }` |
| `broadcast` | `room`, `event`, optional `payload` object | Others in room get `{ event, room, payload, occurred_at }`; caller gets `{ "type": "broadcast_result", "delivered" }` (sender excluded from broadcast) |
| `presence` | `room` | `{ "type": "presence_result", "connection_ids", "by_actor" }` |
| `direct` | `target_actor_id`, `event`, optional `payload` | Recipients: `{ event, room: "__direct__", payload, occurred_at, from_actor_id, target_actor_id }`. Sender: `{ "type": "direct_result", "target_actor_id", "delivered" }`. Requires non-anonymous `actor_id`. |

Malformed JSON or unknown `type` returns `{ "type": "error", "code", "message" }`.

### Capabilities

`GET /sdk/capabilities` includes `features.realtime_websocket` and a `realtime` object with `websocket_path`, `hub_kind` (`in_memory` or `redis_fanout`), and `direct_to_actor_supported`.

---

### Query Spec Reference

## Query spec reference (`QuerySpec` / `SQLAlchemyRepository`)

This document is the **contract** for `eitohforge_sdk.application.dto.repository.QuerySpec` as applied by `eitohforge_sdk.infrastructure.repositories.sqlalchemy_repository.SQLAlchemyRepository`. It aligns with blueprint **§6 Query specification engine** for the SQL path.

### Filter operators

| Operator | Value shape | SQLAlchemy behavior |
|----------|-------------|---------------------|
| `eq` | scalar | `column == value` |
| `ne` | scalar | `column != value` |
| `gt`, `gte`, `lt`, `lte` | scalar | Comparison on the mapped column |
| `contains` | string (typical) | `column.contains(value)` |
| `startswith` | string | `column.startswith(value)` |
| `endswith` | string | `column.endswith(value)` |
| `between` | sequence of **exactly two** elements | `column.between(lo, hi)`; invalid length → filter skipped |
| `in` | non-string **sequence** | `column IN (...)`; **empty sequence** → matches **no rows** (`false()`) |
| `not_in` | non-string sequence | `column NOT IN (...)`; **empty sequence** → **no filter** (all rows pass this predicate) |
| `exists` | boolean | `True` → `IS NOT NULL`, `False` → `IS NULL` on the column (not a SQL `EXISTS` subquery) |

**Strings** are not valid `in` / `not_in` values (use a one-element tuple or list). **Unknown field names** are **silently ignored** (no row filter applied for that condition). To fail fast, call `validate_query_filters_against_columns` from `eitohforge_sdk.application.query_spec_support`.

### Sorting

`SortSpec`: `field` must exist on the model; unknown fields are skipped. Multiple sorts apply in order.

### Pagination

| Mode | Behavior |
|------|----------|
| `offset` | `OFFSET` + `LIMIT` from `pagination.offset` and `page_size`. |
| `cursor` | If `cursor` is numeric, used as **offset**; else falls back to `offset`. |
| `keyset` | Uses first applicable `sort` (or `id` ascending); `cursor` is compared to the sort column (`>` / `<` for asc/desc). |

### Code

```python
from eitohforge_sdk.application import validate_query_filters_against_columns
from eitohforge_sdk.application.dto.repository import FilterCondition, FilterOperator, QuerySpec

validate_query_filters_against_columns(
    query,
    valid_columns={"id", "name", "email", "tenant_id", "score"},
)
```

### Related

- DTO definitions: `src/eitohforge_sdk/application/dto/repository.py`
- Implementation: `src/eitohforge_sdk/infrastructure/repositories/sqlalchemy_repository.py`
- Tests: `tests/unit/test_sqlalchemy_repository.py`, `tests/unit/test_query_spec_support.py`

---

### Operations Runbook

## EitohForge Operations Runbook

Operational baseline for deployment, rollback, and reliability governance.

### 1) Deployment Workflow

- CI quality gates must pass (`ruff`, `mypy`, `pytest`, migration policy).
- Package build must pass reproducibility and metadata checks.
- Security/compliance gates must pass (`pip-audit`, SBOM, license policy).
- Publish to internal registry first (`publish-internal.yml`).
- Promote to production release through environment approvals.

### 2) Release Environments

- `dev`: automatic deploy after merge to protected branch.
- `staging`: deploy candidate from internal registry and run smoke suite.
- `prod`: manual approval required; use release artifact already validated in staging.

### 3) Rollback Procedure

1. Identify target previous version from internal registry.
2. Trigger rollback deployment with previous version pin.
3. Confirm `/ready` and `/status` endpoints report healthy.
4. Validate core API smoke suite and critical business paths.
5. Open post-incident record with root cause and corrective action.

### 4) Incident Severity and Response

- `SEV-1`: full outage or data integrity risk, page immediately.
- `SEV-2`: degraded service with customer impact.
- `SEV-3`: minor degradation or non-critical feature issue.

Escalation path:

- On-call engineer -> platform owner -> engineering lead.

### 5) SLO and Error Budget Baseline

- Availability SLO: `99.9%` monthly for API endpoints.
- p95 latency SLO: `< 300ms` for core read/write paths.
- Error rate SLO: `< 0.5%` 5xx over rolling 30 minutes.

Error budget:

- Monthly downtime budget for 99.9%: ~43.8 minutes.
- If budget burn exceeds 50% mid-cycle, freeze non-critical releases.

### 6) Monitoring and Alerting

- Use telemetry from observability middleware and health endpoints:
  - `/health`
  - `/ready`
  - `/status`
- Alert on:
  - sustained 5xx elevation
  - SLO burn-rate threshold breach
  - readiness check failures

### 7) Change Management Policy

- No direct production deploy from untagged commits.
- Every production release must map to immutable artifacts.
- Schema migrations must be backward-compatible for rolling deployments.

### 8) Operational Checklists

#### Pre-Deploy Checklist

- [ ] Release artifact built in CI with reproducibility checks
- [ ] Vulnerability and license checks green
- [ ] Migration plan reviewed
- [ ] Rollback candidate confirmed

#### Post-Deploy Checklist

- [ ] Readiness/health green
- [ ] No elevated error budget burn
- [ ] Key user journeys validated
- [ ] Incident channel quiet for 30 minutes

### 9) Network and Deployment References

- `docs/guides/tls-and-cert-rotation-runbook.md`
- `docs/guides/mtls-trust-model.md`
- `docs/guides/load-balancing-and-health-routing.md`
- `docs/guides/deployment-strategies-and-rollback-controls.md`

---

### Architecture Spec + Implementation Map

Below is the **complete A–Z backend architecture verdict** for your reusable **FastAPI-based enterprise SDK framework**.
This document defines the **final blueprint** for a low-code, pluggable, production-grade backend platform that can bootstrap any modern API system (ERP, SaaS, tracking platform, trading infra, multiplayer backend, automation stack, etc.).

You can treat this as the **specification document for your backend SDK**.

---

## Backend SDK Architecture — Complete A to Z Blueprint

### Objective

Build a reusable backend framework that:

* generates clean architecture automatically
* supports SQL + NoSQL interchangeably
* enables security middleware on demand
* integrates communication services
* supports SSO and identity federation
* handles sessions, storage, caching, sockets
* supports multi-tenant SaaS systems
* provides CRUD scaffolding
* allows plugin-based extensions
* minimizes boilerplate coding

Target outcome:

```
secureapi create project my_service
```

→ production-ready backend instantly

---

## 1. Core Architectural Philosophy

Use layered clean architecture:

```
Presentation Layer
Application Layer
Domain Layer
Infrastructure Layer
Core Layer
```

Responsibilities:

| Layer          | Role                      |
| -------------- | ------------------------- |
| Presentation   | routers/controllers       |
| Application    | use-cases                 |
| Domain         | entities/business logic   |
| Infrastructure | DB/storage/cache          |
| Core           | config/security/providers |

---

## 2. Project Auto-Generated Folder Structure

```
app/

  main.py

  core/
    config.py
    dependencies.py
    middleware.py
    security.py
    lifecycle.py

  domain/
    entities/
    repositories/
    specifications/

  application/
    use_cases/
    requests/
    responses/
    services/

  infrastructure/
    database/
    cache/
    storage/
    messaging/

  presentation/
    routers/
    controllers/

  modules/
    auth/
    users/

tests/
```

---

## 3. Configuration System (Central Control Engine)

Single config entrypoint:

```python
BackendSDKConfig(
    database="postgres",
    orm="tortoise",
    cache="redis",
    storage="s3",
    enable_sessions=True,
    enable_signature=True,
    enable_socket=True,
    enable_sso=True
)
```

Controls everything dynamically.

---

## 4. Database Layer (Polyglot Persistence Support)

Supports:

| DB         | Use           |
| ---------- | ------------- |
| Postgres   | transactional |
| MySQL      | legacy        |
| SQLite     | local/dev     |
| MongoDB    | document      |
| Elastic    | search        |
| Redis      | cache/session |
| Clickhouse | analytics     |

Architecture:

```
DatabaseRegistry
RepositoryFactory
TransactionManager
SpecificationEngine
```

Example:

```
UserRepository → Postgres
AuditRepository → Mongo
SearchRepository → Elastic
```

---

## 5. Generic Repository Abstraction

Universal interface:

```
create()
get()
update()
delete()
list()
bulk_create()
paginate()
```

Adapters:

```
SQLRepository
MongoRepository
ElasticRepository
RedisRepository
```

Service layer never changes across DB engines.

---

## 6. Query Specification Engine

Unified filter interface:

```
Filter(field="age", operator="gt", value=18)
```

Supports:

```
eq
ne
gt
gte
lt
lte
contains
startswith
endswith
between
exists
```

Works across SQL and Mongo automatically.

---

## 7. CRUD Auto Generator

CLI:

```
secureapi create crud product
```

Creates:

```
entity
repository
service
schema
router
tests
```

Endpoints auto-generated:

```
POST
GET
GET/{id}
PUT/{id}
DELETE
```

---

## 8. Request / Response Model System

Never allow raw dictionaries.

Structure:

```
Request Models
Domain Entities
Response Models
Envelope Models
```

Standard response:

```
ApiResponse[T]
```

Example:

```
success
data
message
error_code
meta
```

---

## 9. Pagination Engine

Supports:

```
offset pagination
cursor pagination
keyset pagination
```

Response:

```
PaginatedResponse[T]
```

---

## 10. Authentication System

Supports:

```
JWT access tokens
refresh token rotation
device binding
session tracking
token revocation
```

Session store options:

```
Redis
Postgres
Memory
```

---

## 11. Session Management Engine

Supports:

```
multi-device login
logout single session
logout all sessions
concurrent session limits
socket session sync
```

Session model:

```
session_id
device_id
user_id
expires_at
ip_address
```

---

## 12. Role-Based Access Control (RBAC)

Example:

```
admin
manager
user
viewer
```

Decorator:

```
@requires_permission("invoice.approve")
```

---

## 13. Attribute-Based Access Control (ABAC)

Example:

```
user.department == resource.department
```

Policy engine:

```
@policy("can_edit_profile")
```

---

## 14. Identity Federation & SSO

Supports:

```
Google
Microsoft
Apple
Facebook
Azure AD
Okta
Keycloak
SAML
OIDC
```

Flow:

```
External provider
→ Identity Broker
→ Internal user mapping
→ Internal JWT issued
```

Multi-tenant SSO routing supported.

---

## 15. Session + JWT Unified Identity Model

Architecture:

```
Access Token → Stateless
Refresh Token → Stateful
Session Store → Revocation Control
```

---

## 16. Storage Abstraction Layer

Providers:

```
Local storage
AWS S3
Azure Blob
MinIO
GCS
```

Unified interface:

```
upload()
download()
delete()
exists()
generate_url()
```

---

## 17. Presigned URL Engine

Supports:

```
upload URLs
download URLs
temporary access URLs
```

Example:

```
generate_presigned_upload()
```

---

## 18. Storage Access Policies

Examples:

```
private
public
owner-only
team-visible
tenant-scoped
```

---

## 19. CDN Integration Layer

Supports:

```
CloudFront
Cloudflare
Azure CDN
```

Auto URL generation:

```
storage.public_url()
```

---

## 20. Distributed Cache Layer

Providers:

```
Redis
Memory
Memcached
```

Supports:

```
TTL
tag invalidation
prefix invalidation
lazy caching
write-through caching
```

Decorator:

```
@cached(ttl=60)
```

---

## 21. Rate Limiting Engine

Supports:

```
per-user
per-IP
per-endpoint
per-role
```

Example:

```
@rate_limit("10/minute")
```

---

## 22. Notification Gateway Layer

Unified interface:

```
send_email()
send_sms()
send_whatsapp()
send_push()
send_template()
```

Providers:

```
SES
SendGrid
SMTP
Twilio
MSG91
Meta WhatsApp
Firebase
SNS
```

---

## 23. Template Messaging Engine

Supports:

```
local templates
database templates
S3 templates
multi-language templates
```

Example:

```
send_template("otp_sms")
```

---

## 24. Background Job Engine

Providers:

```
Celery
Redis Queue
Dramatiq
Kafka
```

Example:

```
@background_task
```

Supports:

```
retry
cron
delay
batch execution
```

---

## 25. External API Client Framework

Unified integration layer:

```
ExternalServiceClient
```

Features:

```
retry policies
timeouts
circuit breakers
logging
auth injection
rate control
```

Example:

```
maps.get_distance()
payments.create_order()
```

---

## 26. Webhook Framework

Supports:

```
signature verification
event routing
retries
dead-letter queues
```

Example:

```
@webhook_handler("payment.success")
```

---

## 27. Event Bus Architecture

Example:

```
UserCreatedEvent
```

Handlers:

```
SendWelcomeEmailHandler
CreateAuditLogHandler
AssignPermissionsHandler
```

---

## 28. Multi-Database Support

Registry:

```
primary DB
analytics DB
document DB
search DB
cache DB
```

Usage:

```
db_registry.get("analytics")
```

---

## 29. Distributed Transaction Support

Supports:

```
local transactions
saga orchestration
event-driven consistency
```

---

## 30. Search Engine Integration

Providers:

```
ElasticSearch
OpenSearch
MeiliSearch
```

Example:

```
search.index()
search.query()
```

---

## 31. Audit Logging Engine

Tracks:

```
login
logout
CRUD changes
file uploads
permission updates
session revocation
```

Example:

```
audit.log("USER_UPDATED")
```

---

## 32. Security Middleware Stack

Optional modules:

```
signature validation
nonce validation
device binding
token blacklist
IP restriction
geo restriction
rate limiting
```

---

## 33. Request Signing Engine

Headers:

```
X-Timestamp
X-Nonce
X-Signature
```

Protects:

```
replay attacks
tampering
automation abuse
```

---

## 34. Capability Negotiation Endpoint

Expose:

```
/sdk/capabilities
```

Example:

```
signature_required
nonce_required
device_binding_required
```

Used by client SDK auto-sync.

---

## 35. Multi-Tenant Architecture Support

Supports:

```
schema-per-tenant
row-level filtering
storage isolation
cache isolation
identity isolation
```

Implementation note:
schema-per-tenant uses Postgres `search_path` (`EITOHFORGE_TENANT_DB_SCHEMA_ISOLATION_ENABLED=true`) with the resolved tenant id interpolated into `EITOHFORGE_TENANT_DB_SCHEMA_NAME_TEMPLATE`.

---

## 36. Plugin System

Allows external modules to register:

```
routes
middlewares
schemas
providers
event handlers
```

Example:

```
register_plugin(InventoryPlugin)
```

---

## 37. Metrics & Observability

Exports:

```
latency
error rate
query time
cache hit rate
socket connections
```

Integrations:

```
Prometheus
Grafana
OpenTelemetry
```

---

## 38. Health Monitoring Endpoints

Auto-generated:

```
/health
/status
/metrics
```

Checks:

```
database
redis
storage
queue
search
```

---

## 39. Secret Management Layer

Providers:

```
environment variables
vault
AWS secrets manager
Azure key vault
```

Usage:

```
secret.get("API_KEY")
```

---

## 40. Unified Security Context Object

Accessible globally:

```
SecurityContext
```

Contains:

```
user
roles
permissions
session
device
tenant
```

Usage:

```
SecurityContext.current_user()
```

---

## 41. Socket Infrastructure

Supports:

```
JWT auth
rooms
presence tracking
broadcast messaging
private messaging
session sync
```

---

## 42. Versioned API Engine

Supports:

```
/v1/users
/v2/users
```

Backward compatibility maintained automatically.

---

## 43. Idempotency Engine

Header:

```
X-Idempotency-Key
```

Prevents duplicate operations.

---

## 44. Feature Flag System

Example:

```
feature_flags.is_enabled("new_dashboard")
```

Supports staged rollouts.

---

## Final Result

This backend SDK becomes a **complete application platform** capable of powering:

* ERP systems
* SaaS platforms
* tracking apps
* trading automation
* multiplayer engines
* document platforms
* notification hubs
* identity providers
* integration middleware

with minimal per-project coding.

---

If you want the next step, I can produce the **module-by-module implementation roadmap (build order + priorities)** so you can start developing this SDK systematically instead of all at once.



I created a **downloadable Markdown architecture document** for your backend SDK:

**Download here:**
[Secure Backend SDK Architecture Blueprint](sandbox:/mnt/data/secure_backend_sdk_architecture.md)

---

## Implementation Plan (Practical Build Roadmap)

Below is the **recommended phased execution strategy** to actually build this backend platform without chaos. Follow this order; each phase unlocks the next layer cleanly.

---

## Phase 0 — Foundation (Week 1)

Goal: Core framework skeleton + config engine

Build:

#### 1. Project generator CLI

Command:

```
secureapi create project <name>
```

Creates:

```
core/
domain/
application/
infrastructure/
presentation/
modules/
```

Tools to use:

* typer (CLI)
* jinja2 (templates)
* cookiecutter-style scaffolding

---

#### 2. BackendSDKConfig

Single control object:

```python
BackendSDKConfig(
    database="postgres",
    orm="tortoise",
    cache="redis",
    storage="s3",
    enable_auth=True
)
```

Everything reads from this.

---

#### 3. ProviderFactory

Core abstraction engine:

```
DatabaseProvider
CacheProvider
StorageProvider
NotificationProvider
AuthProvider
```

Factory resolves implementations dynamically.

---

## Phase 1 — Database Abstraction Layer (Week 2)

Goal: SQL + Mongo interchangeable CRUD

Implement:

#### BaseRepository

```
create()
get()
update()
delete()
list()
paginate()
```

Adapters:

```
SQLRepository
MongoRepository
```

Add:

```
Filter
Sort
Pagination
Specification
TransactionManager
```

Now DB becomes swappable instantly.

---

## Phase 2 — Response Envelope + Error System (Week 2)

Create:

```
ApiResponse[T]
PaginatedResponse[T]
ErrorResponse
```

Add:

```
ExceptionMiddleware
ErrorRegistry
```

Standardizes entire API contract.

---

## Phase 3 — Auth + Session Engine (Week 3)

Implement:

#### JWTManager

```
create_access_token()
create_refresh_token()
verify_token()
```

#### SessionManager

Supports:

```
multi-device login
revoke session
revoke all sessions
session tracking
```

Storage:

```
RedisSessionProvider
DBSessionProvider
```

---

## Phase 4 — RBAC + ABAC (Week 3)

Create:

```
RoleManager
PermissionManager
PolicyEngine
```

Decorators:

```
@requires_permission()
@policy()
```

Attach automatically via middleware.

---

## Phase 5 — Storage Engine + Presigned URLs (Week 4)

Implement:

```
StorageProvider
```

Adapters:

```
Local
S3
Azure Blob
MinIO
```

Add:

```
generate_presigned_upload()
generate_presigned_download()
```

---

## Phase 6 — Cache Engine (Week 4)

Create:

```
CacheProvider
```

Adapters:

```
Redis
Memory
Memcached
```

Add decorator:

```
@cached(ttl=60)
```

---

## Phase 7 — CRUD Generator (Week 5)

CLI:

```
secureapi create crud user
```

Generates:

```
entity
schema
repository
service
router
tests
```

Huge productivity multiplier.

---

## Phase 8 — Notification Gateway (Week 6)

Create:

```
NotificationProvider
```

Adapters:

```
SES
SendGrid
SMTP
Twilio
MSG91
WhatsApp
Firebase
```

Add:

```
template engine
queue support
localization support
```

---

## Phase 9 — External API Client Framework (Week 6)

Create:

```
ExternalServiceClient
```

Features:

```
retry
timeout
circuit breaker
auth injectors
logging
```

Example:

```
maps_client
razorpay_client
digilocker_client
```

---

## Phase 10 — SSO Engine (Week 7)

Create:

```
SSOProvider
IdentityBroker
```

Adapters:

```
Google
Microsoft
Apple
Okta
Azure AD
SAML
OIDC
```

Flow:

```
external login → internal JWT issued
```

---

## Phase 11 — Multi-Database Registry (Week 7)

Enable:

```
primary DB
analytics DB
document DB
search DB
```

Example:

```
db_registry.get("analytics")
```

Supports polyglot persistence.

---

## Phase 12 — Event Bus + Background Jobs (Week 8)

Create:

```
EventBus
BackgroundTaskProvider
```

Adapters:

```
Celery
RedisQueue
Dramatiq
Kafka
```

Example:

```
UserCreatedEvent
```

Triggers handlers automatically.

---

## Phase 13 — Webhook Framework (Week 8)

Add:

```
WebhookManager
```

Supports:

```
signature verification
retry queue
routing
DLQ
```

---

## Phase 14 — Security Middleware Stack (Week 9)

Implement optional modules:

```
SignatureMiddleware
NonceMiddleware
DeviceBindingMiddleware
RateLimitMiddleware
GeoRestrictionMiddleware
```

Controlled via config flags.

---

## Phase 15 — Capability Negotiation Endpoint (Week 9)

Expose:

```
/sdk/capabilities
```

Used by Flutter SDK auto-sync.

Example response:

```
signature_required
nonce_required
device_binding_required
```

---

## Phase 16 — Plugin System (Week 10)

Create:

```
PluginRegistry
```

Plugins can register:

```
routes
middleware
providers
schemas
events
```

Example:

```
register_plugin(InventoryPlugin)
```

---

## Phase 17 — Observability + Health Monitoring (Week 10)

Add:

Endpoints:

```
/health
/status
/metrics
```

Integrations:

```
Prometheus
Grafana
OpenTelemetry
```

---

## Phase 18 — Multi-Tenant Engine (Week 11)

Support:

```
tenant DB schema isolation
tenant cache namespace
tenant storage prefix
tenant SSO mapping
```

Expose:

```
TenantContext.current()
```

---

## Final Result After These Phases

You will have a reusable backend platform comparable in capability to:

* NestJS (Node)
* Spring Boot (Java)
* ASP.NET Core (C#)

—but optimized for FastAPI and mobile-first architectures.

---

## Appendix — EitohForge implementation map (living)

This blueprint predates the **`eitohforge`** CLI and **`eitohforge_sdk`** package. The **target command line** for the shipped product is:

```bash
eitohforge create project <name> [--profile standard|minimal]
```

not `secureapi create`. The table below maps blueprint sections (§1–§44) to the **current** repository state. **Implemented** means a usable baseline exists in tree; **Partial** means the idea is present but narrower than the blueprint; **Planned / gap** means not yet aligned with the spec.

| § | Blueprint topic | Status | Notes |
|---|-----------------|--------|--------|
| 1 | Layered clean architecture | Implemented | Templates + SDK modules follow presentation / application / domain / infrastructure / core. |
| 2 | Generated folder structure | Implemented | `eitohforge create project` scaffolds `app/` layout consistent with the blueprint. |
| 3 | Central configuration | Partial | **`AppSettings`** (`pydantic-settings`, `EITOHFORGE_*`) replaces the sample `BackendSDKConfig` API; feature toggles via env, **`ForgePlatformToggles`**, **`forge_platform_toggles_uniform`**, and **`ForgeAppBuildConfig.wire_*`**. |
| 4 | Polyglot persistence | Partial | **Postgres**, **MySQL** (`MySQLProvider`, `mysql+pymysql`, `pymysql`), **SQLite** in factory + registry roles. **`DatabaseSettings.sqlalchemy_url`** covers all three. **Mongo** etc. still out of scope. |
| 5 | Generic repository | Implemented | **`RepositoryContract`** (Protocol) + **`SqlalchemyRepository`** adapter. |
| 6 | Query specification | Partial | **`QuerySpec`** + **`SQLAlchemyRepository`** document and tests in **`docs/guides/query-spec-reference.md`** (blueprint §6 operators on SQL path; extensions `in` / `not_in`). Optional **`validate_query_filters_against_columns`**. Not a Mongo/document engine or standalone query DSL beyond this. |
| 7 | CRUD auto generator | Partial | **`eitohforge create crud`** ships richer **field types** (optional text, int, bool, datetime, **FK-style** `parent_resource_id`) + **golden** tests; still in-memory service stub, not full SQL CRUD codegen per entity. |
| 8–9 | Request/response + pagination | Implemented | DTOs (`ApiResponse`, pagination types) in application layer. |
| 10–15 | Auth, session, RBAC, ABAC, SSO, JWT+session | Implemented / Partial | JWT, session stores, RBAC helpers, ABAC **`PolicyEngine`**, OIDC/SAML SSO adapters; “unified identity model” depth varies by integration. |
| 16–19 | Storage, presign, policies, CDN | Implemented / Partial | **`StorageProvider`** / **`PresignableStorageProvider`**, local + S3, policy + CDN helpers. |
| 20 | Distributed cache | Implemented | Memory + Redis contracts and factory. |
| 21–23 | Rate limit, notifications, templated messaging | Implemented | Middleware + gateway + template engine baselines. |
| 24–26 | Jobs, external API, webhooks | Implemented | In-memory jobs, HTTP client, webhook dispatcher + signing contracts. |
| 27 | Event bus | Partial | **`InMemoryEventBus`** + **`RedisPublishingEventBus`** (Redis **PUBLISH** sidecar); cross-process **SUBSCRIBE** is app-owned (cookbook). |
| 28–29 | Multi-DB + distributed transactions | Partial | **Registry** + **saga** module; depth below full blueprint. |
| 30 | Search | Partial | Memory + OpenSearch-style adapter; Elasticsearch-specific breadth not guaranteed. |
| 31–33 | Audit, security middleware, request signing | Implemented | Wired through **`build_forge_app`** with toggles. |
| 34 | Capabilities endpoint | Implemented | **`/sdk/capabilities`** (+ profile for auth/runtime/realtime). |
| 35–36 | Multi-tenant + plugins | Implemented | Tenant middleware + **`PluginRegistry`**. |
| 37–38 | Observability + health | Implemented | Middleware with optional Prometheus request metrics (`/metrics`) + OTEL tracer wiring (sets `x-trace-id` from span context when enabled); health routes remain intact. |
| 39 | Secret management | Implemented | **`VaultSecretProvider`** implements the `SecretProvider` contract via Vault KV read (best-effort) and is wired in `build_secret_provider` for `EITOHFORGE_SECRET_PROVIDER=vault`. Value extraction supports common KV v2/v1 shapes; unit tests mock HTTP responses (no caching, so rotation is picked up on re-fetch). |
| 40 | Security context | Implemented | Request-scoped context middleware. |
| 41 | Sockets | Partial | **`InMemorySocketHub`** / **`RedisFanoutSocketHub`** (multi-worker **broadcast** + **`direct`** to `actor_id` via Redis); **`/realtime/ws`**; **room “privacy”** is naming-only; **authorization** for who may join or direct-message whom is **application-owned** (documented in **`realtime-websocket.md`**). |
| 42 | Versioned API | Partial | **`ApiVersion`**, **`build_versioned_router`**, **`ApiVersioningSettings`** + deprecation headers on **`/v1`** via **`build_forge_app`**; separate OpenAPI per mount documented in cookbook. |
| 43–44 | Idempotency + feature flags | Implemented | Header-based idempotency + feature flag service and endpoint. |

**Conclusion:** The blueprint is **not** fully implemented line-for-line; it remains the **north star**. The SDK covers a large subset of §1–§44 with **protocol-first** infra boundaries where it matters (storage, DB provider, repositories). Gaps cluster around **additional database engines**, **richer query/event systems**, **socket private channels**, and **operations/secret backends**. Use this appendix when prioritizing roadmap items; keep it updated when major capabilities land.

---

For day-to-day usage, see **`docs/guides/usage-complete.md`**, **`docs/guides/forge-profiles.md`**, and **`docs/standards/engineering-standards.md`**.

To close remaining gaps vs this specification, see **`docs/roadmap/blueprint-completion-waves.md`** and execution board Phase 17 (`P17-*`).

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
