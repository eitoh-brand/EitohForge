from __future__ import annotations

from fastapi import FastAPI

from eitohforge_sdk.core.plugins import PluginRegistry


class SamplePlugin:
    name = "sample"

    def register_routes(self, app: FastAPI) -> None:
        @app.get("/plugins/sample")
        def sample_route() -> dict[str, str]:
            return {"plugin": "sample"}

    def register_providers(self, registry: dict[str, object]) -> None:
        registry["sample.provider"] = object()

    def register_events(self, registry: dict[str, tuple[object, ...]]) -> None:
        registry["sample.event"] = (object(),)


def test_plugin_registry_registers_and_applies_hooks() -> None:
    registry = PluginRegistry()
    plugin = SamplePlugin()
    app = FastAPI()
    providers: dict[str, object] = {}
    events: dict[str, tuple[object, ...]] = {}

    registry.register(plugin)
    applied = registry.apply(app=app, provider_registry=providers, event_registry=events)

    assert registry.has("sample")
    assert applied == ("sample",)
    assert "sample.provider" in providers
    assert "sample.event" in events
    assert any(route.path == "/plugins/sample" for route in app.routes)
