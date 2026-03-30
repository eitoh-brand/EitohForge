"""Identifier-oriented value objects."""

from __future__ import annotations

from dataclasses import dataclass
import re
from uuid import UUID

from eitohforge_sdk.domain.value_objects.errors import DomainInvariantError


_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_\-:.]{1,127}$")
_TENANT_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_\-]{1,63}$")


@dataclass(frozen=True)
class EntityId:
    value: str

    def __post_init__(self) -> None:
        if not _ID_PATTERN.fullmatch(self.value):
            raise DomainInvariantError("EntityId has invalid format.")


@dataclass(frozen=True)
class TenantId:
    value: str

    def __post_init__(self) -> None:
        if not _TENANT_PATTERN.fullmatch(self.value):
            raise DomainInvariantError("TenantId has invalid format.")


@dataclass(frozen=True)
class CorrelationId:
    value: str

    def __post_init__(self) -> None:
        try:
            UUID(self.value)
        except Exception as exc:
            raise DomainInvariantError("CorrelationId must be a valid UUID.") from exc

