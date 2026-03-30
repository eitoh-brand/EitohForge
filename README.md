# EitohForge

**EitohForge** is an enterprise-focused Python package: a **FastAPI-oriented SDK** (`eitohforge_sdk`) plus a **CLI** (`eitohforge`) for scaffolding layered backends, migrations, and local multi-service dev. Runtime settings use the `EITOHFORGE_*` prefix (see generated `.env.example` and [usage-complete](docs/guides/usage-complete.md)).

---

## Installation

### From PyPI (recommended)

Requires **Python 3.12+**.

```bash
python -m pip install eitohforge
```

Install the CLI into an isolated tool environment (optional):

```bash
pipx install eitohforge
```

Verify:

```bash
eitohforge --help
eitohforge version
```

### With uv

```bash
uv tool install eitohforge
# or inside a project:
uv add eitohforge
```

### From source (development)

```bash
git clone https://github.com/eitoh-brand/EitohForge.git
cd EitohForge
uv sync --all-extras
uv run eitohforge --help
```

---

## SDK usage

The library is published as **`eitohforge`**; import the SDK from **`eitohforge_sdk`**.

### Minimal app (capabilities + health)

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

See `examples/example-minimal/` for a runnable variant.

### Full platform wiring (middleware, health family, platform routes)

Use **`build_forge_app`** from `eitohforge_sdk.core` with **`ForgeAppBuildConfig`** (feature flags, settings, toggles, etc.):

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

See `examples/example-enterprise/` for a fuller example.

### Discovery and configuration

- **`GET /sdk/capabilities`** — enabled features and contract hints (headers, tenant, realtime, observability, etc.).
- **Settings** — `AppSettings` / `get_settings()`; all env keys are documented in [usage-complete](docs/guides/usage-complete.md) and in generated `.env.example`).
- **Deeper topics** — auth, tenant, migrations, realtime, observability: [usage-complete](docs/guides/usage-complete.md), [cookbook](docs/guides/cookbook.md).

---

## CLI usage

Top-level help:

```bash
eitohforge --help
```

### `eitohforge version`

Prints the installed package version (same as `importlib.metadata.version("eitohforge")`).

### `eitohforge create`

Scaffold projects and CRUD modules.

```bash
# New project (SDK-first: depends on eitohforge / eitohforge-sdk at runtime)
eitohforge create project my_service

# Parent directory and profile
eitohforge create project my_service --path . --profile standard

# Standalone scaffold (no runtime SDK dependency in pyproject)
eitohforge create project my_service --mode standalone

# CRUD module inside an existing generated project (requires app/)
cd my_service
eitohforge create crud orders --path .
```

Help:

```bash
eitohforge create --help
eitohforge create project --help
eitohforge create crud --help
```

### `eitohforge db`

Alembic helpers (run from the generated project root, where `alembic.ini` lives).

```bash
eitohforge db init
eitohforge db migrate -m "describe change"
eitohforge db upgrade
eitohforge db downgrade
eitohforge db current
```

Help:

```bash
eitohforge db --help
eitohforge db migrate --help
```

### `eitohforge dev`

Run multiple Uvicorn processes from a **`forge.dev.json`** manifest (multi-port local dev).

```bash
eitohforge dev --path .
eitohforge dev validate --path .
```

Help:

```bash
eitohforge dev --help
eitohforge dev validate --help
```

---

## Documentation

| Guide | Purpose |
|--------|
| [docs/guides/usage-complete.md](docs/guides/usage-complete.md) | Install, config, auth, tenant, DB, migrations, realtime, observability |
| [docs/guides/cookbook.md](docs/guides/cookbook.md) | Recipes and patterns |
| [docs/guides/enterprise-readiness-checklist.md](docs/guides/enterprise-readiness-checklist.md) | Production readiness |
| [docs/guides/python-packaging-and-publishing.md](docs/guides/python-packaging-and-publishing.md) | Packaging and publishing |

---

## Examples

- **`examples/example-minimal/`** — smallest SDK-backed app (health + `/sdk/capabilities`).
- **`examples/example-enterprise/`** — `build_forge_app` middleware stack and sample routes.

---

## License

Proprietary — see `pyproject.toml` metadata.
