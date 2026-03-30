"""CRUD generator template fragments and rendering helpers."""

from dataclasses import dataclass

from jinja2 import Template


@dataclass(frozen=True)
class CrudTemplateContext:
    """Context values used by CRUD module templates."""

    module_name: str
    class_name: str
    resource_name: str


CRUD_MODULE_FILE_TEMPLATES: dict[str, str] = {
    "__init__.py": '''"""CRUD module for {{ resource_name }}."""

from app.modules.{{ module_name }}.router import router
from app.modules.{{ module_name }}.schema import (
    {{ class_name }}Create,
    {{ class_name }}Read,
    {{ class_name }}Update,
)

__all__ = ["router", "{{ class_name }}Create", "{{ class_name }}Read", "{{ class_name }}Update"]
''',
    "schema.py": """from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class {{ class_name }}Create(BaseModel):
    \"\"\"Create payload: common field types + optional FK-style relation stub.\"\"\"

    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=2000)
    quantity: int = Field(default=1, ge=0, le=1_000_000)
    is_active: bool = True
    parent_resource_id: str | None = Field(
        default=None,
        max_length=64,
        description="Optional link to another resource id (foreign-key style stub; no DB join enforced here).",
    )
    due_at: datetime | None = None


class {{ class_name }}Update(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=2000)
    quantity: int | None = Field(default=None, ge=0, le=1_000_000)
    is_active: bool | None = None
    parent_resource_id: str | None = Field(default=None, max_length=64)
    due_at: datetime | None = None


class {{ class_name }}Read(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    description: str | None
    quantity: int
    is_active: bool
    parent_resource_id: str | None
    due_at: datetime | None
""",
    "service.py": """from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from app.application.dto.repository import QuerySpec
from app.application.dto.response import ApiResponse, ApiResponseMeta, PaginatedApiResponse, PaginationMeta
from app.application.services.validation import ServiceValidationHooks
from app.core.validation.context import ValidationContext
from app.modules.{{ module_name }}.schema import (
    {{ class_name }}Create,
    {{ class_name }}Read,
    {{ class_name }}Update,
)


@dataclass
class _{{ class_name }}Record:
    id: str
    name: str
    description: str | None
    quantity: int
    is_active: bool
    parent_resource_id: str | None
    due_at: datetime | None


def _to_read(record: _{{ class_name }}Record) -> {{ class_name }}Read:
    return {{ class_name }}Read(
        id=record.id,
        name=record.name,
        description=record.description,
        quantity=record.quantity,
        is_active=record.is_active,
        parent_resource_id=record.parent_resource_id,
        due_at=record.due_at,
    )


class {{ class_name }}Service:
    def __init__(self) -> None:
        self._items: dict[str, _{{ class_name }}Record] = {}
        self._validation = ServiceValidationHooks()

    async def create(self, payload: {{ class_name }}Create, context: ValidationContext) -> ApiResponse:
        await self._validation.validate_or_raise(payload, context)
        record = _{{ class_name }}Record(
            id=str(uuid4()),
            name=payload.name,
            description=payload.description,
            quantity=payload.quantity,
            is_active=payload.is_active,
            parent_resource_id=payload.parent_resource_id,
            due_at=payload.due_at,
        )
        self._items[record.id] = record
        return ApiResponse(
            data=_to_read(record),
            message="{{ class_name }} created",
            meta=_response_meta(context),
        )

    async def list(self, query: QuerySpec, context: ValidationContext) -> PaginatedApiResponse:
        await self._validation.validate_or_raise(query, context)
        values = tuple(self._items.values())
        offset = query.pagination.offset
        page_size = query.pagination.page_size
        page = values[offset : offset + page_size]
        return PaginatedApiResponse(
            data=tuple(_to_read(item) for item in page),
            pagination=PaginationMeta(total=len(values), page_size=page_size),
            message="{{ class_name }} list",
            meta=_response_meta(context),
        )

    async def update(
        self, entity_id: str, payload: {{ class_name }}Update, context: ValidationContext
    ) -> ApiResponse:
        await self._validation.validate_or_raise(payload, context)
        item = self._items.get(entity_id)
        if item is None:
            return ApiResponse(success=False, data=None, message="{{ class_name }} not found")
        if payload.name is not None:
            item.name = payload.name
        if payload.description is not None:
            item.description = payload.description
        if payload.quantity is not None:
            item.quantity = payload.quantity
        if payload.is_active is not None:
            item.is_active = payload.is_active
        if payload.parent_resource_id is not None:
            item.parent_resource_id = payload.parent_resource_id
        if payload.due_at is not None:
            item.due_at = payload.due_at
        return ApiResponse(
            data=_to_read(item),
            message="{{ class_name }} updated",
            meta=_response_meta(context),
        )

    async def delete(self, entity_id: str, context: ValidationContext) -> ApiResponse:
        await self._validation.validate_or_raise({"entity_id": entity_id}, context)
        deleted = self._items.pop(entity_id, None) is not None
        return ApiResponse(
            data={"deleted": deleted},
            message="{{ class_name }} deleted" if deleted else "{{ class_name }} not found",
            meta=_response_meta(context),
        )


def _response_meta(context: ValidationContext) -> ApiResponseMeta:
    return ApiResponseMeta(request_id=context.request_id, trace_id=context.trace_id)
""",
    "router.py": """from fastapi import APIRouter, Request

from app.application.dto.repository import QuerySpec
from app.application.dto.response import ApiResponse, PaginatedApiResponse
from app.core.security_context import get_request_security_context
from app.core.validation.context import ValidationContext, ValidationStage
from app.modules.{{ module_name }}.schema import (
    {{ class_name }}Create,
    {{ class_name }}Update,
)
from app.modules.{{ module_name }}.service import {{ class_name }}Service

router = APIRouter(prefix="/{{ resource_name }}", tags=["{{ resource_name }}"])
service = {{ class_name }}Service()


def _build_validation_context(request: Request) -> ValidationContext:
    security_context = get_request_security_context(request)
    return ValidationContext(
        stage=ValidationStage.REQUEST,
        actor_id=security_context.actor_id,
        tenant_id=security_context.tenant_id,
        request_id=security_context.request_id,
        trace_id=security_context.trace_id,
    )


@router.post("/", response_model=ApiResponse)
async def create_{{ resource_name }}(payload: {{ class_name }}Create, request: Request) -> ApiResponse:
    return await service.create(payload, _build_validation_context(request))


@router.post("/search", response_model=PaginatedApiResponse)
async def list_{{ resource_name }}(query: QuerySpec, request: Request) -> PaginatedApiResponse:
    return await service.list(query, _build_validation_context(request))


@router.patch("/{entity_id}", response_model=ApiResponse)
async def update_{{ resource_name }}(
    entity_id: str, payload: {{ class_name }}Update, request: Request
) -> ApiResponse:
    return await service.update(entity_id, payload, _build_validation_context(request))


@router.delete("/{entity_id}", response_model=ApiResponse)
async def delete_{{ resource_name }}(entity_id: str, request: Request) -> ApiResponse:
    return await service.delete(entity_id, _build_validation_context(request))
""",
}

CRUD_TEST_FILE_TEMPLATE = """from datetime import UTC, datetime

import asyncio

from app.application.dto.repository import QuerySpec
from app.core.validation.context import ValidationContext, ValidationStage
from app.modules.{{ module_name }}.schema import {{ class_name }}Create, {{ class_name }}Update
from app.modules.{{ module_name }}.service import {{ class_name }}Service


def _context() -> ValidationContext:
    return ValidationContext(stage=ValidationStage.REQUEST)


def test_{{ module_name }}_service_crud_cycle() -> None:
    service = {{ class_name }}Service()
    due = datetime(2030, 6, 15, 12, 0, tzinfo=UTC)

    created = asyncio.run(
        service.create(
            {{ class_name }}Create(
                name="first",
                description="A row",
                quantity=3,
                is_active=False,
                parent_resource_id="parent-xyz",
                due_at=due,
            ),
            _context(),
        )
    )
    assert created.success is True
    entity_id = getattr(created.data, "id")
    assert getattr(created.data, "quantity") == 3
    assert getattr(created.data, "parent_resource_id") == "parent-xyz"
    assert getattr(created.data, "due_at") == due

    listed = asyncio.run(service.list(QuerySpec(), _context()))
    assert listed.success is True
    assert listed.pagination.total >= 1

    updated = asyncio.run(
        service.update(entity_id, {{ class_name }}Update(name="second", quantity=5), _context())
    )
    assert updated.success is True
    assert getattr(updated.data, "name") == "second"
    assert getattr(updated.data, "quantity") == 5

    deleted = asyncio.run(service.delete(entity_id, _context()))
    assert deleted.success is True
    assert deleted.data == {"deleted": True}
"""


def build_crud_context(module_name: str) -> CrudTemplateContext:
    """Build a CRUD template context from a module name."""
    normalized_module = module_name.lower()
    class_name = "".join(part.capitalize() for part in normalized_module.split("_"))
    return CrudTemplateContext(
        module_name=normalized_module,
        class_name=class_name,
        resource_name=normalized_module,
    )


def render_crud_module_templates(context: CrudTemplateContext) -> dict[str, str]:
    """Render all CRUD template files for a module."""
    rendered: dict[str, str] = {}
    for relative_path, raw_template in CRUD_MODULE_FILE_TEMPLATES.items():
        rendered[relative_path] = Template(raw_template).render(
            module_name=context.module_name,
            class_name=context.class_name,
            resource_name=context.resource_name,
        )
    return rendered


def render_crud_project_templates(context: CrudTemplateContext) -> dict[str, str]:
    """Render CRUD templates mapped to full project-relative paths."""
    project_templates: dict[str, str] = {}
    for relative_path, content in render_crud_module_templates(context).items():
        project_templates[f"app/modules/{context.module_name}/{relative_path}"] = content
    project_templates[f"tests/test_{context.module_name}_crud.py"] = Template(CRUD_TEST_FILE_TEMPLATE).render(
        module_name=context.module_name,
        class_name=context.class_name,
        resource_name=context.resource_name,
    )
    return project_templates
