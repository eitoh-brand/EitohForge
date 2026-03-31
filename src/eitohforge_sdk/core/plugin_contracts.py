"""Typed protocols for :class:`PluginRegistry` hooks (static checking + documentation)."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from fastapi import FastAPI


@runtime_checkable
class RoutePlugin(Protocol):
    """Plugin that registers FastAPI routes on the main app."""

    name: str

    def register_routes(self, app: FastAPI) -> None:
        """Mount routers or add routes to ``app``."""


@runtime_checkable
class ProviderPlugin(Protocol):
    """Plugin that registers infrastructure providers into a string-keyed registry."""

    name: str

    def register_providers(self, registry: dict[str, Any]) -> None:
        """Populate ``registry`` with provider instances or factories."""


@runtime_checkable
class EventsPlugin(Protocol):
    """Plugin that registers domain/event handlers."""

    name: str

    def register_events(self, registry: dict[str, tuple[Any, ...]]) -> None:
        """Register event type keys to handler tuples."""
