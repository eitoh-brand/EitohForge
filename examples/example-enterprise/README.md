# Example Enterprise (EitohForge)

Reference layout for a **production-style** FastAPI app using the SDK (`build_forge_app`):

- Security hardening headers + host / body limits
- Observability (request/trace IDs, metrics sink)
- Security context middleware
- Global error handlers
- Tenant isolation middleware (config-driven)
- Health / readiness / status (`register_health_endpoints`)
- Capability profile (`/sdk/capabilities`)
- Feature flags (`/sdk/feature-flags`) with a registered demo flag

For a **full generated** layered app (CRUD, DB, webhooks, search, sockets), use:

```bash
eitohforge create project my_service
```

## Prerequisite

From the **EitohForge repository root**:

```bash
uv pip install -e .
uv pip install -e "examples/example-enterprise[dev]"
```

## Run

```bash
cd examples/example-enterprise
uvicorn example_enterprise.main:app --reload --host 0.0.0.0 --port 8010
```

Multi-process dev (same pattern as generated repos) using the repo-root CLI and `forge.dev.json`:

```bash
cd examples/example-enterprise
eitohforge dev --path .
```

## Test

```bash
cd examples/example-enterprise
pytest
```

## Notes

- Readiness/status run with **no custom checks** by default (empty check map), so `/ready` reports ready.
- Enable stricter tenant or signing behavior via `EITOHFORGE_*` environment variables (see `.env.example`).
