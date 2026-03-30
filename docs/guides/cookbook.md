# EitohForge Cookbook

Practical recipes for common implementation patterns.

## 1) Enable Strict Tenant Isolation

Set:

- `EITOHFORGE_TENANT_ENABLED=true`
- `EITOHFORGE_TENANT_REQUIRED_FOR_WRITE_METHODS=true`
- `EITOHFORGE_TENANT_RESOURCE_TENANT_HEADER=x-resource-tenant-id`

Behavior:

- write methods without tenant context are denied (`403`)
- cross-tenant access via mismatched resource tenant header is denied (`403`)

## 2) Add a Plugin Module

Implement a plugin object with a unique `name`, optionally:

- `register_routes(app)`
- `register_providers(registry)`
- `register_events(registry)`

Register it with `PluginRegistry.register(plugin)` and apply with `PluginRegistry.apply(...)`.

## 3) Roll Out a Feature Gradually

Use `FeatureFlagService` and register:

- `FeatureFlagDefinition(key="new-ui", rollout_percentage=10)`

Then evaluate with actor/tenant context:

- `FeatureFlagTargetingContext(actor_id="actor-1", tenant_id="tenant-a")`

Expose runtime values via `register_feature_flags_endpoint(app)`.

## 4) Harden HTTP Surface

Use `register_security_hardening_middleware` with `SecurityHardeningRule` to:

- enforce max request size
- restrict allowed hosts
- set strict response security headers

## 5) Baseline and Check Performance

Generate baseline:

- `uv run python scripts/performance_baseline.py --mode baseline`

Run regression check:

- `uv run python scripts/performance_baseline.py --mode check --threshold 25`

## 6) Realtime WebSocket (generated apps)

- Ensure `EITOHFORGE_REALTIME_ENABLED=true` (default).
- Connect to `/realtime/ws` with a valid **access** JWT (`?token=...` or `Authorization: Bearer ...`).
- Use JSON frames: `join` / `leave` / `broadcast` / `direct` / `presence` / `ping` — see `docs/guides/realtime-websocket.md`.
- **Single worker:** default in-memory hub only.
- **Multi-worker (`EITOHFORGE_REALTIME_REDIS_URL`):** `RedisFanoutSocketHub` **PUBLISH**es each client **`broadcast`** and **`direct`** to peers; **`presence` / `room_members` stay per process**. Private “rooms” are a **naming convention** only; **`direct`** targets `actor_id` (JWT subject) and does **not** enforce authorization—see `realtime-websocket.md`.
- **Manual two-worker check:** run Redis; start two Uvicorn processes with the same `EITOHFORGE_REALTIME_REDIS_URL`; connect WebSockets on different workers, join the same room, broadcast from one — the other should receive the event. Expect each worker’s `presence` to list only its local connections.

## 7) Deprecate `/v1` with HTTP headers

`build_forge_app` registers deprecation middleware automatically. Enable with:

- `EITOHFORGE_API_VERSION_DEPRECATE_V1=true`
- Optional `EITOHFORGE_API_VERSION_V1_SUNSET_HTTP_DATE` (e.g. `Sat, 31 Dec 2026 23:59:59 GMT`)
- Optional `EITOHFORGE_API_VERSION_V1_LINK_DEPRECATION` (URL for `Link: <...>; rel="deprecation"`)

Responses for paths starting with `/v1` then include `Deprecation: true` plus `Sunset` / `Link` when set.

## 8) Versioned OpenAPI documents

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

## 9) Event bus: local + Redis publish

- In-process: `InMemoryEventBus` from `eitohforge_sdk.infrastructure.messaging`.
- Cross-process fan-out: `build_redis_publishing_event_bus(redis_url="redis://localhost:6379/0")` implements `EventBus`; `publish` notifies local subscribers and `PUBLISH`es JSON to `eitohforge:evt:{event_name}`.

Other workers must run a Redis `SUBSCRIBE` loop (or use a task queue) to consume those messages; the SDK does not start a background subscriber in the web process.

## 10) Observability: Prometheus + OTEL

### Prometheus metrics (`/metrics`)

- Enable: `EITOHFORGE_OBSERVABILITY_ENABLE_PROMETHEUS=true`
- Path: `EITOHFORGE_OBSERVABILITY_PROMETHEUS_METRICS_PATH` (default: `/metrics`)

Request metrics are exported using a per-app Prometheus registry:

- `eitohforge_http_requests_total{method,path,status}`
- `eitohforge_http_requests_duration_ms{method,path,status}`

### OTEL tracing

- Enable: `EITOHFORGE_OBSERVABILITY_OTEL_ENABLED=true`
- Service name: `EITOHFORGE_OBSERVABILITY_OTEL_SERVICE_NAME` (default: `eitohforge`)
- OTLP traces over HTTP (optional): `EITOHFORGE_OBSERVABILITY_OTEL_OTLP_HTTP_ENDPOINT`

When enabled, responses include `x-trace-id` (derived from the active OTEL span context when available).
