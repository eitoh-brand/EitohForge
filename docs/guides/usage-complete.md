# EitohForge — Complete Usage Guide

End-to-end reference for installing the SDK/CLI, configuring services, and operating generated applications.

## 1) Install

### From source (development)

```bash
git clone https://github.com/eitoh-brand/EitohForge.git
cd EitohForge
uv pip install -e ".[dev]"
eitohforge --help
```

### From an internal package index

```bash
pip install eitohforge
```

Verify:

```bash
eitohforge version
python -c "import eitohforge_sdk; print('ok')"
```

## 2) Create a project

**SDK-first (default)** — generated apps depend on `eitohforge` / `eitohforge-sdk` for core middleware and primitives:

```bash
eitohforge create project my_service
```

**Profile** — default `standard` (most platform features on in `.env.example`). Use `--profile minimal` for a slimmer default and enable features via env when needed (see `docs/guides/forge-profiles.md`).

**Standalone** — self-contained copies of SDK patterns inside the repo (no runtime SDK dependency):

```bash
eitohforge create project my_service --mode standalone
```

### Add a CRUD module

```bash
cd my_service
eitohforge create crud orders --path .
```

## 3) Configuration

- All runtime settings use the `EITOHFORGE_*` prefix (see generated `.env.example`).
- Layered files: `.env`, then `.env.local`, then process environment (see `pydantic-settings` model config in `AppSettings`).
- **Production**: set `EITOHFORGE_APP_ENV` to `dev`, `staging`, or `prod` and supply a real `EITOHFORGE_AUTH_JWT_SECRET` (local allows the placeholder).

### Environments (`EITOHFORGE_APP_ENV`)

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

## 4) Migrations (Alembic)

Generated projects include `migrations/` and `alembic.ini`.

```bash
cd my_service
eitohforge db init          # first-time
eitohforge db migrate -m "message"
eitohforge db upgrade
eitohforge db current
```

CI enforces migration policy via `scripts/check_migration_policy.py` (destructive changes require an explicit approval marker).

## 5) Authentication and authorization

- **JWT**: `JwtTokenManager` (access/refresh, rotation) — see `app.core.auth` in generated apps.
- **Sessions**: Redis-backed session manager with revocation hooks.
- **RBAC**: `require_roles` dependency from headers (`x-roles`, `x-actor-id`).
- **ABAC**: policy engine and `require_policies` for tenant-aware routes.
- **SSO**: `SsoBroker` with OIDC/SAML adapters (`OidcSsoProvider`, `SamlSsoProvider`).

## 6) Plugins and extension

- Implement a `PluginModule` (name + optional `register_routes` / `register_providers` / `register_events`).
- Register with `PluginRegistry` and call `apply(...)` during startup.

## 7) Deploy and operate

- **Health**: `GET /health`, `GET /ready`, `GET /status`.
- **Runbook**: `docs/guides/operations-runbook.md`.
- **TLS / LB / rollout**: `docs/guides/tls-and-cert-rotation-runbook.md`, `load-balancing-and-health-routing.md`, `deployment-strategies-and-rollback-controls.md`.

Container-style run (example):

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 8) Packaging and release

- Build: `python -m build` (reproducibility checks in CI).
- Publish: internal workflow `publish-internal.yml`; optional PyPI `publish-pypi.yml`.
- Details: `docs/guides/python-packaging-and-publishing.md`.

## 9) Troubleshooting

| Symptom | Check |
|---------|--------|
| Startup fails on config | Env vars and `AppSettings` validators (`EITOHFORGE_APP_ENV`, JWT secret). |
| 403 on writes | Tenant middleware: `x-tenant-id` / `EITOHFORGE_TENANT_*`. |
| 429 responses | Rate limit headers and `EITOHFORGE_RATE_LIMIT_*`. |
| 401 on signed APIs | Request signing secret and clock skew (`EITOHFORGE_REQUEST_SIGNING_*`). |
| DB connection errors | `EITOHFORGE_DB_*`, driver (`postgresql+psycopg`, `mysql+pymysql`, `sqlite`), port (3306 vs 5432), and network reachability. |
| Import errors in SDK mode | `pip install eitohforge` and matching version in generated `pyproject.toml`. |

## 10) Reference examples

- **Minimal**: `examples/example-minimal/` — capabilities + health.
- **Enterprise-style**: `examples/example-enterprise/` — hardening, observability, tenant, flags, health family.

See each example’s `README.md` for run and test commands.

## 11) Further reading

- `docs/guides/cookbook.md`
- `docs/guides/realtime-websocket.md`
- `docs/guides/forge-profiles.md` (includes `forge_platform_toggles_uniform`)
- `docs/guides/query-spec-reference.md` — `QuerySpec` operators and `SQLAlchemyRepository` behavior
- Repository root `secure_backend_sdk_architecture.md` — specification; see its appendix for implementation coverage vs §1–§44
- `docs/guides/enterprise-readiness-checklist.md`
- `docs/guides/testing-and-example-project-strategy.md`
- `docs/roadmap/architecture-coverage-matrix.md`
