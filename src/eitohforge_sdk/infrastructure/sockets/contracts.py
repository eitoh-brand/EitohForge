"""Socket infrastructure contracts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol


@dataclass(frozen=True)
class SocketPrincipal:
    """Authenticated socket principal details."""

    actor_id: str
    tenant_id: str | None = None
    claims: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SocketEnvelope:
    """Outbound socket payload envelope."""

    event: str
    room: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class SocketConnection(Protocol):
    """Socket connection contract."""

    async def send_json(self, payload: Mapping[str, Any]) -> None:
        ...

    async def close(self, code: int = 1000, reason: str | None = None) -> None:
        ...
