"""JWT access/refresh token manager with rotation support."""

from __future__ import annotations

import base64
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
import hashlib
import hmac
import json
from typing import Any, Protocol
from uuid import uuid4


class TokenType(str, Enum):
    """Token kinds supported by the manager."""

    ACCESS = "access"
    REFRESH = "refresh"


@dataclass(frozen=True)
class TokenPair:
    """Issued access and refresh tokens."""

    access_token: str
    refresh_token: str


@dataclass
class RefreshTokenRecord:
    """Refresh token persistence state."""

    subject: str
    tenant_id: str | None
    expires_at: datetime
    revoked: bool = False


class JwtTokenError(ValueError):
    """Base JWT manager error."""


class InvalidTokenError(JwtTokenError):
    """Raised for malformed or unverifiable tokens."""


class TokenExpiredError(JwtTokenError):
    """Raised when an otherwise valid token has expired."""


class RefreshTokenReplayError(JwtTokenError):
    """Raised when an old refresh token is reused."""


class RefreshTokenStore(Protocol):
    """Refresh token state store protocol."""

    def put(self, jti: str, record: RefreshTokenRecord) -> None:
        ...

    def get(self, jti: str) -> RefreshTokenRecord | None:
        ...

    def revoke(self, jti: str) -> None:
        ...


@dataclass
class InMemoryRefreshTokenStore:
    """In-memory refresh token state store."""

    records: dict[str, RefreshTokenRecord]

    def __init__(self) -> None:
        self.records = {}

    def put(self, jti: str, record: RefreshTokenRecord) -> None:
        self.records[jti] = record

    def get(self, jti: str) -> RefreshTokenRecord | None:
        return self.records.get(jti)

    def revoke(self, jti: str) -> None:
        record = self.records.get(jti)
        if record is not None:
            record.revoked = True


class JwtTokenManager:
    """Issue, validate, and rotate access/refresh JWT tokens."""

    def __init__(
        self,
        *,
        secret: str,
        access_ttl: timedelta = timedelta(minutes=15),
        refresh_ttl: timedelta = timedelta(days=7),
        issuer: str | None = None,
        audience: str | None = None,
        refresh_store: RefreshTokenStore | None = None,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        if len(secret) < 32:
            raise ValueError("JWT secret must be at least 32 characters.")
        self._secret = secret.encode("utf-8")
        self._access_ttl = access_ttl
        self._refresh_ttl = refresh_ttl
        self._issuer = issuer
        self._audience = audience
        self._refresh_store = refresh_store or InMemoryRefreshTokenStore()
        self._now_provider = now_provider or (lambda: datetime.now(UTC))

    def issue_token_pair(
        self,
        *,
        subject: str,
        tenant_id: str | None = None,
        additional_claims: Mapping[str, Any] | None = None,
    ) -> TokenPair:
        """Issue an access token and refresh token pair."""
        access_token = self._issue_token(
            token_type=TokenType.ACCESS,
            subject=subject,
            ttl=self._access_ttl,
            tenant_id=tenant_id,
            additional_claims=additional_claims,
        )
        refresh_token, refresh_jti, refresh_exp = self._issue_token_with_metadata(
            token_type=TokenType.REFRESH,
            subject=subject,
            ttl=self._refresh_ttl,
            tenant_id=tenant_id,
            additional_claims=additional_claims,
        )
        self._refresh_store.put(
            refresh_jti,
            RefreshTokenRecord(subject=subject, tenant_id=tenant_id, expires_at=refresh_exp),
        )
        return TokenPair(access_token=access_token, refresh_token=refresh_token)

    def decode_and_validate(
        self, token: str, *, expected_type: TokenType | None = None
    ) -> dict[str, Any]:
        """Decode token and validate signature, claims, and expiry."""
        header_segment, payload_segment, signature_segment = _split_token(token)
        signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")
        expected_signature = _sign(signing_input, self._secret)
        if not hmac.compare_digest(expected_signature, signature_segment):
            raise InvalidTokenError("JWT signature validation failed.")

        payload = _decode_json(payload_segment)
        if not isinstance(payload, dict):
            raise InvalidTokenError("JWT payload must be an object.")

        token_type = payload.get("typ")
        if expected_type is not None and token_type != expected_type.value:
            raise InvalidTokenError(f"Expected token type '{expected_type.value}'.")

        exp = payload.get("exp")
        if not isinstance(exp, int):
            raise InvalidTokenError("JWT payload missing numeric 'exp' claim.")
        now_ts = int(self._now_provider().timestamp())
        if exp <= now_ts:
            raise TokenExpiredError("JWT token has expired.")

        if self._issuer is not None and payload.get("iss") != self._issuer:
            raise InvalidTokenError("JWT issuer does not match expected issuer.")
        if self._audience is not None and payload.get("aud") != self._audience:
            raise InvalidTokenError("JWT audience does not match expected audience.")

        return payload

    def rotate_refresh_token(self, refresh_token: str) -> TokenPair:
        """Rotate a refresh token and issue a fresh token pair."""
        claims = self.decode_and_validate(refresh_token, expected_type=TokenType.REFRESH)
        jti = claims.get("jti")
        if not isinstance(jti, str):
            raise InvalidTokenError("Refresh token missing 'jti' claim.")

        record = self._refresh_store.get(jti)
        if record is None or record.revoked:
            raise RefreshTokenReplayError("Refresh token has already been used or revoked.")
        if record.expires_at <= self._now_provider():
            self._refresh_store.revoke(jti)
            raise TokenExpiredError("Refresh token session has expired.")

        self._refresh_store.revoke(jti)
        return self.issue_token_pair(subject=record.subject, tenant_id=record.tenant_id)

    def revoke_refresh_token(self, refresh_token: str) -> None:
        """Revoke a refresh token by its token identifier."""
        claims = self.decode_and_validate(refresh_token, expected_type=TokenType.REFRESH)
        jti = claims.get("jti")
        if not isinstance(jti, str):
            raise InvalidTokenError("Refresh token missing 'jti' claim.")
        self._refresh_store.revoke(jti)

    def _issue_token(
        self,
        *,
        token_type: TokenType,
        subject: str,
        ttl: timedelta,
        tenant_id: str | None,
        additional_claims: Mapping[str, Any] | None,
    ) -> str:
        token, _, _ = self._issue_token_with_metadata(
            token_type=token_type,
            subject=subject,
            ttl=ttl,
            tenant_id=tenant_id,
            additional_claims=additional_claims,
        )
        return token

    def _issue_token_with_metadata(
        self,
        *,
        token_type: TokenType,
        subject: str,
        ttl: timedelta,
        tenant_id: str | None,
        additional_claims: Mapping[str, Any] | None,
    ) -> tuple[str, str, datetime]:
        now = self._now_provider()
        expires_at = now + ttl
        jti = str(uuid4())
        payload: dict[str, Any] = {
            "sub": subject,
            "typ": token_type.value,
            "jti": jti,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
        }
        if tenant_id is not None:
            payload["tenant_id"] = tenant_id
        if self._issuer is not None:
            payload["iss"] = self._issuer
        if self._audience is not None:
            payload["aud"] = self._audience
        if additional_claims is not None:
            payload.update(dict(additional_claims))

        token = _encode_token(payload=payload, secret=self._secret)
        return (token, jti, expires_at)


def _encode_token(*, payload: dict[str, Any], secret: bytes) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_segment = _encode_json(header)
    payload_segment = _encode_json(payload)
    signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")
    signature = _sign(signing_input, secret)
    return f"{header_segment}.{payload_segment}.{signature}"


def _split_token(token: str) -> tuple[str, str, str]:
    parts = token.split(".")
    if len(parts) != 3:
        raise InvalidTokenError("JWT token must have exactly three segments.")
    return (parts[0], parts[1], parts[2])


def _sign(data: bytes, secret: bytes) -> str:
    digest = hmac.new(secret, data, hashlib.sha256).digest()
    return _base64url_encode(digest)


def _encode_json(value: dict[str, Any]) -> str:
    raw = json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return _base64url_encode(raw)


def _decode_json(segment: str) -> Any:
    raw = _base64url_decode(segment)
    return json.loads(raw.decode("utf-8"))


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    try:
        return base64.urlsafe_b64decode(value + padding)
    except Exception as exc:
        raise InvalidTokenError("JWT segment is not valid base64url.") from exc

