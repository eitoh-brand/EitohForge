# Plugins guide

This guide describes how **Forge plugins** extend an application: optional route registration, provider wiring, and event hook registration through `PluginRegistry`.

## Concepts

- **Plugin object**: Any object with a non-empty `name` and optional methods `register_routes(app)`, `register_providers(registry)`, `register_events(registry)`. The registry uses duck typing (`hasattr` checks).
- **Typed contracts** (for static checks and documentation): `RoutePlugin`, `ProviderPlugin`, `EventsPlugin` in `eitohforge_sdk.core.plugin_contracts`.
- **Registry**: `eitohforge_sdk.core.plugins.PluginRegistry` stores plugins by normalized name and applies them in one pass.

## Registering plugins

```python
from fastapi import FastAPI
from eitohforge_sdk.core.plugins import PluginRegistry

registry = PluginRegistry()
registry.register(my_plugin)

def wire_plugins(app: FastAPI) -> None:
    provider_map: dict[str, object] = {}
    event_map: dict[str, tuple[object, ...]] = {}
    registry.apply(app=app, provider_registry=provider_map, event_registry=event_map)
```

Pass only the keyword arguments your plugins need. If a plugin does not implement a hook, it is skipped.

## Route plugins

Implement `register_routes(self, app: FastAPI) -> None` and mount routers with `app.include_router(...)` or add routes directly. Keep prefixes and tags consistent with your API surface.

## Provider plugins

`register_providers` receives a **mutable dict** (string key → provider instance or factory). Application composition can read this map when constructing services.

## Event plugins

`register_events` receives a registry mapping event type keys to handler tuples. The exact shape depends on your domain; the SDK supplies the hook point so plugins stay decoupled from core wiring.

## CLI scaffold

Generate a starter package under `app/plugins/<name>/`:

```bash
eitohforge create plugin <name> --path /path/to/your/project
```

This creates a class with `name`, `register_routes`, `register_providers`, and `register_events` stubs aligned with the patterns above.

## Naming and collisions

- Plugin `name` is normalized to lowercase; duplicates overwrite the previous registration.
- Use distinct route prefixes per plugin (for example `/plugins/<name>` in the generated stub).

## Related

- Cookbook overview: `docs/guides/cookbook.md` (section “Add a Plugin Module”).
- Architecture diagram: `docs/architecture/platform-overview.md`.
- Framework evolution status: `docs/roadmap/framework-evolution-v0.2-to-v1.md`.
