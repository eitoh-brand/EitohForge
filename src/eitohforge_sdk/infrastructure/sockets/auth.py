"""Socket authentication helpers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from eitohforge_sdk.core.auth import JwtTokenManager, TokenType
from eitohforge_sdk.infrastructure.sockets.contracts import SocketPrincipal


class SocketAuthenticationError(PermissionError):
    """Raised when socket authentication fails."""


@dataclass
class JwtSocketAuthenticator:
    """Authenticate socket clients using access JWT tokens."""

    token_manager: JwtTokenManager
    expected_type: TokenType = TokenType.ACCESS

    def authenticate(self, token: str) -> SocketPrincipal:
        try:
            claims = self.token_manager.decode_and_validate(token, expected_type=self.expected_type)
        except Exception as exc:
            raise SocketAuthenticationError("Socket authentication failed.") from exc

        actor_id = claims.get("sub")
        if not isinstance(actor_id, str) or not actor_id.strip():
            raise SocketAuthenticationError("Socket token subject is missing.")
        tenant_id = claims.get("tenant_id")
        return SocketPrincipal(
            actor_id=actor_id,
            tenant_id=tenant_id if isinstance(tenant_id, str) else None,
            claims=claims,
        )


def extract_socket_token(
    *,
    query_params: Mapping[str, str] | None = None,
    headers: Mapping[str, str] | None = None,
    query_key: str = "token",
    header_name: str = "authorization",
) -> str | None:
    """Extract bearer token from socket handshake query/header."""
    query = query_params or {}
    token = query.get(query_key)
    if isinstance(token, str) and token.strip():
        return token.strip()

    resolved_headers = {key.lower(): value for key, value in (headers or {}).items()}
    raw_auth = resolved_headers.get(header_name.lower())
    if not isinstance(raw_auth, str):
        return None
    prefix = "bearer "
    if raw_auth.lower().startswith(prefix):
        candidate = raw_auth[len(prefix) :].strip()
        return candidate if candidate else None
    return raw_auth.strip() or None
