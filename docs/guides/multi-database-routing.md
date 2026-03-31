# Multi-database routing

Use **`DatabaseRegistry`** to register **`DatabaseProvider`** instances under **logical roles** (for example `primary`, `analytics`, `search`). Use **`RepositoryBindingMap`** to map **domain repository names** (strings used in your composition root) to those roles.

## Built-in registry (`build_database_registry`)

`eitohforge_sdk.infrastructure.database.factory.build_database_registry` registers:

- **`primary`** — always, from `AppSettings.database`
- **`analytics`** — when `EITOHFORGE_DB_ANALYTICS_ENABLED=true`, from `AppSettings.database_analytics`
- **`search`** — when `EITOHFORGE_DB_SEARCH_ENABLED=true`, from `AppSettings.database_search`

Each role’s provider exposes `dsn()` for SQLAlchemy URLs and `ping()` for health checks.

## Binding logical repositories to roles

```python
from eitohforge_sdk.infrastructure.database import DatabaseRegistry, RepositoryBindingMap
from eitohforge_sdk.infrastructure.database.factory import build_database_registry
from eitohforge_sdk.core.config import get_settings

settings = get_settings()
registry = build_database_registry(settings)

bindings = RepositoryBindingMap()
bindings.bind("orders", "primary")
bindings.bind("audit_log", "analytics")

role = bindings.resolve("orders")
provider = registry.get(role)
engine_url = provider.dsn()
```

Use `resolve_or("unknown", "primary")` when a logical name may be absent and you want a default role.

## Wiring SQLAlchemy engines

`EngineRegistry` (see `eitohforge_sdk.infrastructure.engine_registry`) pairs with `DatabaseRegistry` to hold **named SQLAlchemy engines** per role. Application startup typically:

1. Builds `DatabaseRegistry` from settings.
2. Creates one `Engine` per role you need for repositories.
3. Injects the correct engine (or session factory) into `SQLAlchemyRepository` constructors based on `RepositoryBindingMap.resolve(...)`.

Generated projects may only wire `primary` by default; add engines and bindings when you split read models or analytics databases.
