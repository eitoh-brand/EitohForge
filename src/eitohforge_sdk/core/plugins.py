"""Plugin registry for routes/providers/events."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from fastapi import FastAPI


class PluginModule(Protocol):
    """Plugin module contract."""

    name: str


@dataclass
class PluginRegistry:
    """Registry that coordinates plugin self-registration hooks."""

    _plugins: dict[str, PluginModule] = field(default_factory=dict)

    def register(self, plugin: PluginModule) -> None:
        key = plugin.name.strip().lower()
        if not key:
            raise ValueError("Plugin name is required.")
        self._plugins[key] = plugin

    def has(self, plugin_name: str) -> bool:
        return plugin_name.strip().lower() in self._plugins

    def list_names(self) -> tuple[str, ...]:
        return tuple(sorted(self._plugins.keys()))

    def apply(
        self,
        *,
        app: FastAPI | None = None,
        provider_registry: dict[str, Any] | None = None,
        event_registry: dict[str, tuple[Any, ...]] | None = None,
    ) -> tuple[str, ...]:
        for plugin in self._plugins.values():
            if app is not None and hasattr(plugin, "register_routes"):
                getattr(plugin, "register_routes")(app)
            if provider_registry is not None and hasattr(plugin, "register_providers"):
                getattr(plugin, "register_providers")(provider_registry)
            if event_registry is not None and hasattr(plugin, "register_events"):
                getattr(plugin, "register_events")(event_registry)
        return self.list_names()
