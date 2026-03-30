"""Auth core template fragments."""

CORE_AUTH_FILE_TEMPLATES: dict[str, str] = {
    'app/core/auth/__init__.py': """from app.core.auth.jwt import (
    InMemoryRefreshTokenStore,
    InvalidTokenError,
    JwtTokenError,
    JwtTokenManager,
    RefreshTokenReplayError,
    TokenExpiredError,
    TokenPair,
    TokenType,
)
from app.core.auth.session import (
    InMemorySessionStore,
    RedisSessionStore,
    SessionError,
    SessionExpiredError,
    SessionManager,
    SessionNotFoundError,
    SessionRecord,
    SessionRevokedError,
    build_session_store,
)
from app.core.auth.sso import (
    ExternalIdentity,
    InMemorySsoLinkStore,
    SsoBroker,
    SsoError,
    SsoIdentityNotLinkedError,
    SsoLinkStore,
    SsoLoginResult,
    SsoProvider,
    SsoProviderNotFoundError,
)
from app.core.auth.sso_adapters import (
    OidcExchangeError,
    OidcSsoProvider,
    SamlExchangeError,
    SamlSsoProvider,
    SsoAdapterError,
)
""",
    'app/core/auth/jwt.py': """from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
import hashlib
import hmac
import json
from typing import Any
from uuid import uuid4


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str


@dataclass
class RefreshTokenRecord:
    subject: str
    tenant_id: str | None
    expires_at: datetime
    revoked: bool = False


class JwtTokenError(ValueError):
    pass


class InvalidTokenError(JwtTokenError):
    pass


class TokenExpiredError(JwtTokenError):
    pass


class RefreshTokenReplayError(JwtTokenError):
    pass


@dataclass
class InMemoryRefreshTokenStore:
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
    def __init__(
        self,
        *,
        secret: str,
        access_ttl: timedelta = timedelta(minutes=15),
        refresh_ttl: timedelta = timedelta(days=7),
    ) -> None:
        if len(secret) < 32:
            raise ValueError("JWT secret must be at least 32 characters.")
        self._secret = secret.encode("utf-8")
        self._access_ttl = access_ttl
        self._refresh_ttl = refresh_ttl
        self._store = InMemoryRefreshTokenStore()

    def issue_token_pair(self, *, subject: str, tenant_id: str | None = None) -> TokenPair:
        access_token = self._issue_token(TokenType.ACCESS, subject, self._access_ttl, tenant_id)
        refresh_token, refresh_jti, refresh_exp = self._issue_token_with_metadata(
            TokenType.REFRESH, subject, self._refresh_ttl, tenant_id
        )
        self._store.put(
            refresh_jti,
            RefreshTokenRecord(subject=subject, tenant_id=tenant_id, expires_at=refresh_exp),
        )
        return TokenPair(access_token=access_token, refresh_token=refresh_token)

    def decode_and_validate(self, token: str, *, expected_type: TokenType | None = None) -> dict[str, Any]:
        header_segment, payload_segment, signature_segment = _split_token(token)
        signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")
        expected_signature = _sign(signing_input, self._secret)
        if not hmac.compare_digest(expected_signature, signature_segment):
            raise InvalidTokenError("JWT signature validation failed.")

        payload = _decode_json(payload_segment)
        if not isinstance(payload, dict):
            raise InvalidTokenError("JWT payload must be an object.")
        if expected_type is not None and payload.get("typ") != expected_type.value:
            raise InvalidTokenError(f"Expected token type '{expected_type.value}'.")
        exp = payload.get("exp")
        if not isinstance(exp, int) or exp <= int(datetime.now(UTC).timestamp()):
            raise TokenExpiredError("JWT token has expired.")
        return payload

    def rotate_refresh_token(self, refresh_token: str) -> TokenPair:
        claims = self.decode_and_validate(refresh_token, expected_type=TokenType.REFRESH)
        jti = claims.get("jti")
        if not isinstance(jti, str):
            raise InvalidTokenError("Refresh token missing 'jti' claim.")
        record = self._store.get(jti)
        if record is None or record.revoked:
            raise RefreshTokenReplayError("Refresh token has already been used or revoked.")
        if record.expires_at <= datetime.now(UTC):
            self._store.revoke(jti)
            raise TokenExpiredError("Refresh token session has expired.")
        self._store.revoke(jti)
        return self.issue_token_pair(subject=record.subject, tenant_id=record.tenant_id)

    def _issue_token(
        self, token_type: TokenType, subject: str, ttl: timedelta, tenant_id: str | None
    ) -> str:
        token, _, _ = self._issue_token_with_metadata(token_type, subject, ttl, tenant_id)
        return token

    def _issue_token_with_metadata(
        self, token_type: TokenType, subject: str, ttl: timedelta, tenant_id: str | None
    ) -> tuple[str, str, datetime]:
        now = datetime.now(UTC)
        exp = now + ttl
        jti = str(uuid4())
        payload: dict[str, Any] = {
            "sub": subject,
            "typ": token_type.value,
            "jti": jti,
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
        }
        if tenant_id is not None:
            payload["tenant_id"] = tenant_id
        return (_encode_token(payload=payload, secret=self._secret), jti, exp)


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
    return json.loads(_base64url_decode(segment).decode("utf-8"))


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
""",
    'app/core/auth/session.py': """from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
import importlib
import json
from typing import Any, Literal
from uuid import uuid4


class SessionError(ValueError):
    pass


class SessionNotFoundError(SessionError):
    pass


class SessionRevokedError(SessionError):
    pass


class SessionExpiredError(SessionError):
    pass


@dataclass
class SessionRecord:
    session_id: str
    subject: str
    tenant_id: str | None
    created_at: datetime
    expires_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)
    revoked_at: datetime | None = None

    def is_active(self, now: datetime) -> bool:
        return self.revoked_at is None and self.expires_at > now


@dataclass
class InMemorySessionStore:
    _records: dict[str, SessionRecord] = field(default_factory=dict)
    _subject_index: dict[str, set[str]] = field(default_factory=dict)

    def put(self, record: SessionRecord) -> None:
        self._records[record.session_id] = record
        self._subject_index.setdefault(record.subject, set()).add(record.session_id)

    def get(self, session_id: str) -> SessionRecord | None:
        return self._records.get(session_id)

    def revoke(self, session_id: str, *, revoked_at: datetime) -> bool:
        record = self._records.get(session_id)
        if record is None:
            return False
        if record.revoked_at is not None:
            return True
        record.revoked_at = revoked_at
        return True

    def list_by_subject(self, subject: str) -> tuple[SessionRecord, ...]:
        ids = self._subject_index.get(subject, set())
        return tuple(
            record
            for session_id in ids
            if (record := self._records.get(session_id)) is not None
        )


class RedisSessionStore:
    def __init__(self, *, redis_url: str, key_prefix: str = "eitohforge:sessions") -> None:
        try:
            redis_module = importlib.import_module("redis")
        except ModuleNotFoundError as exc:
            raise RuntimeError("Redis session store requires 'redis'. Install via `pip install redis`.") from exc
        self._redis = redis_module.Redis.from_url(redis_url, decode_responses=True)
        self._key_prefix = key_prefix

    def put(self, record: SessionRecord) -> None:
        session_key = self._session_key(record.session_id)
        subject_key = self._subject_key(record.subject)
        self._redis.hset(
            session_key,
            mapping={
                "subject": record.subject,
                "tenant_id": record.tenant_id or "",
                "created_at": record.created_at.isoformat(),
                "expires_at": record.expires_at.isoformat(),
                "revoked_at": record.revoked_at.isoformat() if record.revoked_at is not None else "",
                "metadata": json.dumps(record.metadata, separators=(",", ":"), sort_keys=True),
            },
        )
        self._redis.sadd(subject_key, record.session_id)
        ttl_seconds = max(1, int((record.expires_at - datetime.now(UTC)).total_seconds()))
        self._redis.expire(session_key, ttl_seconds)
        self._redis.expire(subject_key, ttl_seconds)

    def get(self, session_id: str) -> SessionRecord | None:
        raw = self._redis.hgetall(self._session_key(session_id))
        if not raw:
            return None
        return SessionRecord(
            session_id=session_id,
            subject=raw["subject"],
            tenant_id=raw.get("tenant_id") or None,
            created_at=datetime.fromisoformat(raw["created_at"]),
            expires_at=datetime.fromisoformat(raw["expires_at"]),
            revoked_at=datetime.fromisoformat(raw["revoked_at"]) if raw.get("revoked_at") else None,
            metadata=json.loads(raw.get("metadata", "{}")),
        )

    def revoke(self, session_id: str, *, revoked_at: datetime) -> bool:
        session_key = self._session_key(session_id)
        if not self._redis.exists(session_key):
            return False
        self._redis.hset(session_key, mapping={"revoked_at": revoked_at.isoformat()})
        return True

    def list_by_subject(self, subject: str) -> tuple[SessionRecord, ...]:
        session_ids = self._redis.smembers(self._subject_key(subject))
        records: list[SessionRecord] = []
        for session_id in session_ids:
            record = self.get(session_id)
            if record is not None:
                records.append(record)
        return tuple(records)

    def _session_key(self, session_id: str) -> str:
        return f"{self._key_prefix}:session:{session_id}"

    def _subject_key(self, subject: str) -> str:
        return f"{self._key_prefix}:subject:{subject}"


class SessionManager:
    def __init__(
        self,
        *,
        store: InMemorySessionStore | RedisSessionStore | None = None,
        default_ttl: timedelta = timedelta(days=7),
    ) -> None:
        self._store = store or InMemorySessionStore()
        self._default_ttl = default_ttl

    def create_session(
        self,
        *,
        subject: str,
        tenant_id: str | None = None,
        ttl: timedelta | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SessionRecord:
        now = datetime.now(UTC)
        expires_at = now + (ttl or self._default_ttl)
        record = SessionRecord(
            session_id=str(uuid4()),
            subject=subject,
            tenant_id=tenant_id,
            created_at=now,
            expires_at=expires_at,
            metadata=metadata or {},
        )
        self._store.put(record)
        return record

    def validate_session(self, session_id: str) -> SessionRecord:
        record = self._store.get(session_id)
        if record is None:
            raise SessionNotFoundError(f"Session not found: {session_id}")
        now = datetime.now(UTC)
        if record.revoked_at is not None:
            raise SessionRevokedError(f"Session is revoked: {session_id}")
        if record.expires_at <= now:
            raise SessionExpiredError(f"Session is expired: {session_id}")
        return record

    def revoke_session(self, session_id: str) -> bool:
        return self._store.revoke(session_id, revoked_at=datetime.now(UTC))

    def revoke_all_sessions(self, subject: str) -> int:
        count = 0
        now = datetime.now(UTC)
        for record in self._store.list_by_subject(subject):
            if self._store.revoke(record.session_id, revoked_at=now):
                count += 1
        return count


def build_session_store(
    *,
    provider: Literal["memory", "redis"] = "memory",
    redis_url: str | None = None,
    key_prefix: str = "eitohforge:sessions",
) -> InMemorySessionStore | RedisSessionStore:
    if provider == "memory":
        return InMemorySessionStore()
    if provider == "redis":
        if redis_url is None:
            raise ValueError("redis_url is required for redis session store provider.")
        return RedisSessionStore(redis_url=redis_url, key_prefix=key_prefix)
    raise ValueError(f"Unsupported session store provider: {provider}")
""",
    'app/core/auth/sso.py': """from dataclasses import dataclass, field
from typing import Any, Protocol

from app.core.auth.jwt import JwtTokenManager, TokenPair
from app.core.auth.session import SessionManager


@dataclass(frozen=True)
class ExternalIdentity:
    provider: str
    subject: str
    email: str | None = None
    display_name: str | None = None
    tenant_id: str | None = None
    claims: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SsoLoginResult:
    provider: str
    external_subject: str
    internal_subject: str
    token_pair: TokenPair
    session_id: str
    is_new_link: bool


class SsoError(ValueError):
    pass


class SsoProviderNotFoundError(SsoError):
    pass


class SsoIdentityNotLinkedError(SsoError):
    pass


class SsoProvider(Protocol):
    name: str

    def exchange_authorization_code(
        self, *, code: str, redirect_uri: str | None = None, state: str | None = None
    ) -> ExternalIdentity:
        ...


class SsoLinkStore(Protocol):
    def resolve_subject(self, *, provider: str, external_subject: str) -> str | None:
        ...

    def upsert_link(self, *, provider: str, external_subject: str, internal_subject: str) -> None:
        ...


@dataclass
class InMemorySsoLinkStore:
    _links: dict[tuple[str, str], str] = field(default_factory=dict)

    def resolve_subject(self, *, provider: str, external_subject: str) -> str | None:
        return self._links.get((provider.strip().lower(), external_subject))

    def upsert_link(self, *, provider: str, external_subject: str, internal_subject: str) -> None:
        self._links[(provider.strip().lower(), external_subject)] = internal_subject


@dataclass
class SsoBroker:
    jwt_manager: JwtTokenManager
    session_manager: SessionManager
    providers: tuple[SsoProvider, ...] = ()
    link_store: SsoLinkStore = field(default_factory=InMemorySsoLinkStore)
    auto_provision: bool = True
    _providers_by_name: dict[str, SsoProvider] = field(init=False, default_factory=dict)

    def __post_init__(self) -> None:
        self._providers_by_name = {provider.name.strip().lower(): provider for provider in self.providers}

    def register_provider(self, provider: SsoProvider) -> None:
        self._providers_by_name[provider.name.strip().lower()] = provider

    def authenticate(
        self,
        *,
        provider_name: str,
        code: str,
        redirect_uri: str | None = None,
        state: str | None = None,
    ) -> SsoLoginResult:
        provider_key = provider_name.strip().lower()
        provider = self._providers_by_name.get(provider_key)
        if provider is None:
            raise SsoProviderNotFoundError(f"Unknown SSO provider: {provider_name}")

        identity = provider.exchange_authorization_code(code=code, redirect_uri=redirect_uri, state=state)
        internal_subject = self.link_store.resolve_subject(
            provider=provider_key, external_subject=identity.subject
        )

        is_new_link = False
        if internal_subject is None:
            if not self.auto_provision:
                raise SsoIdentityNotLinkedError(
                    f"No internal account link for provider='{provider_key}' subject='{identity.subject}'."
                )
            internal_subject = f"sso:{provider_key}:{identity.subject}"
            self.link_store.upsert_link(
                provider=provider_key,
                external_subject=identity.subject,
                internal_subject=internal_subject,
            )
            is_new_link = True

        token_pair = self.jwt_manager.issue_token_pair(
            subject=internal_subject,
            tenant_id=identity.tenant_id,
            additional_claims={
                "auth_provider": provider_key,
                "external_sub": identity.subject,
            },
        )
        session = self.session_manager.create_session(
            subject=internal_subject,
            tenant_id=identity.tenant_id,
            metadata={
                "auth_provider": provider_key,
                "external_sub": identity.subject,
                "email": identity.email,
            },
        )
        return SsoLoginResult(
            provider=provider_key,
            external_subject=identity.subject,
            internal_subject=internal_subject,
            token_pair=token_pair,
            session_id=session.session_id,
            is_new_link=is_new_link,
        )
""",
    'app/core/auth/sso_adapters.py': """import base64
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any
import json
from xml.etree import ElementTree

from app.core.auth.sso import ExternalIdentity

OidcTokenExchange = Callable[[dict[str, str]], Mapping[str, Any]]


class SsoAdapterError(ValueError):
    pass


class OidcExchangeError(SsoAdapterError):
    pass


class SamlExchangeError(SsoAdapterError):
    pass


@dataclass
class OidcSsoProvider:
    name: str
    token_endpoint: str
    client_id: str
    client_secret: str
    transport: OidcTokenExchange
    default_tenant_claim: str = "tenant_id"

    def exchange_authorization_code(
        self, *, code: str, redirect_uri: str | None = None, state: str | None = None
    ) -> ExternalIdentity:
        _ = state
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "token_endpoint": self.token_endpoint,
        }
        if redirect_uri is not None:
            payload["redirect_uri"] = redirect_uri

        token_response = dict(self.transport(payload))
        id_token = token_response.get("id_token")
        if not isinstance(id_token, str) or not id_token.strip():
            raise OidcExchangeError("OIDC response missing id_token.")
        claims = _decode_jwt_payload_without_verification(id_token)
        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject.strip():
            raise OidcExchangeError("OIDC id_token missing subject claim.")

        tenant_id = claims.get(self.default_tenant_claim) or claims.get("tid")
        return ExternalIdentity(
            provider=self.name,
            subject=subject,
            email=claims.get("email") if isinstance(claims.get("email"), str) else None,
            display_name=claims.get("name") if isinstance(claims.get("name"), str) else None,
            tenant_id=tenant_id if isinstance(tenant_id, str) else None,
            claims=claims,
        )


SamlAssertionParser = Callable[[str], Mapping[str, Any]]


@dataclass
class SamlSsoProvider:
    name: str
    parser: SamlAssertionParser = field(default_factory=lambda: _parse_saml_assertion)
    default_tenant_attribute: str = "tenant_id"

    def exchange_authorization_code(
        self, *, code: str, redirect_uri: str | None = None, state: str | None = None
    ) -> ExternalIdentity:
        _ = (redirect_uri, state)
        try:
            xml_payload = base64.b64decode(code.encode("utf-8"), validate=False).decode("utf-8")
        except Exception as exc:
            raise SamlExchangeError("Invalid SAML response encoding.") from exc

        claims = dict(self.parser(xml_payload))
        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject.strip():
            raise SamlExchangeError("SAML assertion missing subject.")
        tenant_id = claims.get(self.default_tenant_attribute)
        return ExternalIdentity(
            provider=self.name,
            subject=subject,
            email=claims.get("email") if isinstance(claims.get("email"), str) else None,
            display_name=claims.get("name") if isinstance(claims.get("name"), str) else None,
            tenant_id=tenant_id if isinstance(tenant_id, str) else None,
            claims=claims,
        )


def _decode_jwt_payload_without_verification(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise OidcExchangeError("Invalid JWT format for id_token.")
    payload_segment = parts[1]
    padding = "=" * (-len(payload_segment) % 4)
    try:
        payload_bytes = base64.urlsafe_b64decode(payload_segment + padding)
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception as exc:
        raise OidcExchangeError("Unable to decode OIDC id_token payload.") from exc
    if not isinstance(payload, dict):
        raise OidcExchangeError("OIDC id_token payload is not a JSON object.")
    return payload


def _parse_saml_assertion(xml_payload: str) -> Mapping[str, Any]:
    namespaces = {
        "saml2": "urn:oasis:names:tc:SAML:2.0:assertion",
    }
    try:
        root = ElementTree.fromstring(xml_payload)
    except Exception as exc:
        raise SamlExchangeError("Invalid SAML XML payload.") from exc

    subject_node = root.find(".//saml2:Subject/saml2:NameID", namespaces)
    if subject_node is None or not subject_node.text:
        raise SamlExchangeError("SAML NameID is missing.")

    claims: dict[str, Any] = {"sub": subject_node.text.strip()}
    for attribute in root.findall(".//saml2:Attribute", namespaces):
        name = attribute.attrib.get("Name", "").strip()
        if not name:
            continue
        value_node = attribute.find("saml2:AttributeValue", namespaces)
        if value_node is None or value_node.text is None:
            continue
        claims[name] = value_node.text.strip()
    return claims
""",
}
