"""Socket infrastructure primitives."""

from eitohforge_sdk.infrastructure.sockets.auth import (
    JwtSocketAuthenticator,
    SocketAuthenticationError,
    extract_socket_token,
)
from eitohforge_sdk.infrastructure.sockets.contracts import (
    SocketConnection,
    SocketEnvelope,
    SocketHub,
    SocketPrincipal,
)
from eitohforge_sdk.infrastructure.sockets.hub import InMemorySocketHub
from eitohforge_sdk.infrastructure.sockets.presence import (
    PRESENCE_EVENT_JOIN,
    PRESENCE_EVENT_LEAVE,
    PRESENCE_EVENT_UPDATE,
    ActorPresence,
    PresenceManager,
    PresenceStatus,
    RoomPresenceSnapshot,
)
from eitohforge_sdk.infrastructure.sockets.redis_hub import RedisFanoutSocketHub, build_socket_hub_for_settings

__all__ = [
    "SocketAuthenticationError",
    "SocketConnection",
    "SocketEnvelope",
    "SocketHub",
    "SocketPrincipal",
    "JwtSocketAuthenticator",
    "ActorPresence",
    "InMemorySocketHub",
    "PRESENCE_EVENT_JOIN",
    "PRESENCE_EVENT_LEAVE",
    "PRESENCE_EVENT_UPDATE",
    "PresenceManager",
    "PresenceStatus",
    "RedisFanoutSocketHub",
    "RoomPresenceSnapshot",
    "build_socket_hub_for_settings",
    "extract_socket_token",
]
