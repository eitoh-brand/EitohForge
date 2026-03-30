# Example Minimal (EitohForge)

Smallest runnable service that depends on **EitohForge** and exposes:

- `GET /health` — liveness
- `GET /sdk/capabilities` — SDK capability profile (from `register_capabilities_endpoint`)

## Prerequisite

Install the `eitohforge` package (editable from the monorepo root, or from your internal index).

From the **EitohForge repository root**:

```bash
uv pip install -e .
uv pip install -e "examples/example-minimal[dev]"
```

## Run

```bash
cd examples/example-minimal
uvicorn example_minimal.main:app --reload --host 0.0.0.0 --port 8000
```

## Test

```bash
cd examples/example-minimal
pytest
```

## Configuration

Copy `.env.example` to `.env` and adjust. For local development, defaults are valid when `EITOHFORGE_APP_ENV=local`.
