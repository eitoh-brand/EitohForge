"""CLI generators: domain module, infrastructure provider, FastAPI plugin."""

from __future__ import annotations

from dataclasses import dataclass

from jinja2 import Template


def _pascal_case(snake: str) -> str:
    return "".join(part.title() for part in snake.split("_") if part)


@dataclass(frozen=True)
class GeneratorContext:
    """Shared values for `create module|provider|plugin`."""

    name: str
    class_name: str


def build_generator_context(name: str) -> GeneratorContext:
    return GeneratorContext(name=name, class_name=_pascal_case(name))


MODULE_FILE_TEMPLATES: dict[str, str] = {
    "app/modules/{{ name }}/__init__.py": """\"\"\"{{ class_name }} domain module (generated).\"\"\"

from app.modules.{{ name }}.router import router

__all__ = ["router"]
""",
    "app/modules/{{ name }}/schema.py": """\"\"\"Pydantic models for {{ name }}.\"\"\"

from pydantic import BaseModel, ConfigDict, Field


class {{ class_name }}Create(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str = Field(min_length=1, max_length=256)


class {{ class_name }}Read(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    title: str
""",
    "app/modules/{{ name }}/router.py": """\"\"\"HTTP routes for {{ name }}.\"\"\"

from fastapi import APIRouter

from app.modules.{{ name }}.schema import {{ class_name }}Read

router = APIRouter(prefix="/{{ name }}", tags=["{{ name }}"])


@router.get("/example", response_model={{ class_name }}Read)
def example_read() -> {{ class_name }}Read:
    return {{ class_name }}Read(id="example", title="Hello")
""",
}


PROVIDER_FILE_TEMPLATES: dict[str, str] = {
    "app/infrastructure/providers/{{ name }}.py": """\"\"\"Infrastructure provider stub: {{ name }}.\"\"\"

from __future__ import annotations

from typing import Any, Protocol


class {{ class_name }}Provider(Protocol):
    \"\"\"Replace with real methods (e.g. HTTP client, SDK wrapper).\"\"\"

    def ping(self) -> bool:
        ...


class InMemory{{ class_name }}Provider:
    \"\"\"Default no-op implementation for local development.\"\"\"

    def ping(self) -> bool:
        return True


def build_{{ name }}_provider(**_: Any) -> {{ class_name }}Provider:
    \"\"\"Wire settings from ``app.core.config`` when you add real integration.\"\"\"
    return InMemory{{ class_name }}Provider()
""",
}


PLUGIN_FILE_TEMPLATES: dict[str, str] = {
    "app/plugins/{{ name }}/__init__.py": """from app.plugins.{{ name }}.plugin import {{ class_name }}Plugin

__all__ = ["{{ class_name }}Plugin"]
""",
    "app/plugins/{{ name }}/plugin.py": """\"\"\"Forge plugin: {{ name }} (routes + optional registry hooks).\"\"\"

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, FastAPI


class {{ class_name }}Plugin:
    \"\"\"Plugin registered via :class:`eitohforge_sdk.core.plugins.PluginRegistry`.\"\"\"

    name = "{{ name }}"

    def register_routes(self, app: FastAPI) -> None:
        router = APIRouter(prefix="/plugins/{{ name }}", tags=["plugin-{{ name }}"])

        @router.get("/health")
        def health() -> dict[str, str]:
            return {"plugin": "{{ name }}", "status": "ok"}

        app.include_router(router)

    def register_providers(self, registry: dict[str, Any]) -> None:
        \"\"\"Optional: register provider factories on ``registry``.\"\"\"
        _ = registry

    def register_events(self, registry: dict[str, tuple[Any, ...]]) -> None:
        \"\"\"Optional: domain event subscriptions.\"\"\"
        _ = registry
""",
}


def _render_mapping(mapping: dict[str, str], ctx: GeneratorContext) -> dict[str, str]:
    out: dict[str, str] = {}
    data = {"name": ctx.name, "class_name": ctx.class_name}
    for rel, tmpl in mapping.items():
        path = Template(rel).render(**data)
        content = Template(tmpl).render(**data)
        out[path] = content
    return out


def render_module_templates(ctx: GeneratorContext) -> dict[str, str]:
    return _render_mapping(MODULE_FILE_TEMPLATES, ctx)


def render_provider_templates(ctx: GeneratorContext) -> dict[str, str]:
    return _render_mapping(PROVIDER_FILE_TEMPLATES, ctx)


def render_plugin_templates(ctx: GeneratorContext) -> dict[str, str]:
    return _render_mapping(PLUGIN_FILE_TEMPLATES, ctx)
