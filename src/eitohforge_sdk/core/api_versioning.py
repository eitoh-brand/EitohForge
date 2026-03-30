"""API versioning helpers for FastAPI router registration."""

from __future__ import annotations

from enum import Enum

from fastapi import APIRouter, FastAPI


class ApiVersion(str, Enum):
    """Supported API versions."""

    V1 = "v1"
    V2 = "v2"


def build_versioned_router(version: ApiVersion, *routers: APIRouter) -> APIRouter:
    """Compose routers under a version prefix like `/v1`."""
    root = APIRouter(prefix=f"/{version.value}")
    for router in routers:
        root.include_router(router)
    return root


def register_versioned_routers(app: FastAPI, version_routers: dict[ApiVersion, tuple[APIRouter, ...]]) -> None:
    """Register grouped routers for each API version."""
    for version, routers in version_routers.items():
        app.include_router(build_versioned_router(version, *routers))

