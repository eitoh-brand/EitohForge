"""Session management abstractions and implementations."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
import importlib
import json
from typing import Any, Callable, Literal, Protocol, cast
from uuid import uuid4


class SessionError(ValueError):
    """Base session manager error."""


class SessionNotFoundError(SessionError):
    """Raised when a session id cannot be found."""


class SessionRevokedError(SessionError):
    """Raised when a session has been revoked."""


class SessionExpiredError(SessionError):
    """Raised when a session has expired."""


@dataclass
class SessionRecord:
    """Session data persisted by the session manager."""

    session_id: str
    subject: str
    tenant_id: str | None
    created_at: datetime
    expires_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)
    revoked_at: datetime | None = None

    def is_active(self, now: datetime) -> bool:
        return self.revoked_at is None and self.expires_at > now


class SessionStore(Protocol):
    """Session persistence store contract."""

    def put(self, record: SessionRecord) -> None:
        ...

    def get(self, session_id: str) -> SessionRecord | None:
        ...

    def revoke(self, session_id: str, *, revoked_at: datetime) -> bool:
        ...

    def list_by_subject(self, subject: str) -> tuple[SessionRecord, ...]:
        ...


@dataclass
class InMemorySessionStore:
    """In-memory session store suitable for tests and local development."""

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
    """Redis-backed session store (optional dependency)."""

    def __init__(self, *, redis_url: str, key_prefix: str = "eitohforge:sessions") -> None:
        self._redis = self._build_redis_client(redis_url)
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
        raw = cast(dict[str, str], self._redis.hgetall(self._session_key(session_id)))
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
        session_ids = cast(set[str], self._redis.smembers(self._subject_key(subject)))
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

    @staticmethod
    def _build_redis_client(redis_url: str) -> Any:
        try:
            redis_module = importlib.import_module("redis")
        except ModuleNotFoundError as exc:
            raise RuntimeError("Redis session store requires 'redis'. Install via `pip install redis`.") from exc
        redis_client = redis_module.Redis.from_url(redis_url, decode_responses=True)
        return redis_client


class SessionManager:
    """Session lifecycle manager with revoke/revoke-all controls."""

    def __init__(
        self,
        *,
        store: SessionStore | None = None,
        default_ttl: timedelta = timedelta(days=7),
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self._store = store or InMemorySessionStore()
        self._default_ttl = default_ttl
        self._now_provider = now_provider or (lambda: datetime.now(UTC))

    def create_session(
        self,
        *,
        subject: str,
        tenant_id: str | None = None,
        ttl: timedelta | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> SessionRecord:
        now = self._now_provider()
        expires_at = now + (ttl or self._default_ttl)
        record = SessionRecord(
            session_id=str(uuid4()),
            subject=subject,
            tenant_id=tenant_id,
            created_at=now,
            expires_at=expires_at,
            metadata=dict(metadata or {}),
        )
        self._store.put(record)
        return record

    def get_session(self, session_id: str) -> SessionRecord | None:
        return self._store.get(session_id)

    def validate_session(self, session_id: str) -> SessionRecord:
        record = self._store.get(session_id)
        if record is None:
            raise SessionNotFoundError(f"Session not found: {session_id}")
        now = self._now_provider()
        if record.revoked_at is not None:
            raise SessionRevokedError(f"Session is revoked: {session_id}")
        if record.expires_at <= now:
            raise SessionExpiredError(f"Session is expired: {session_id}")
        return record

    def revoke_session(self, session_id: str) -> bool:
        return self._store.revoke(session_id, revoked_at=self._now_provider())

    def revoke_all_sessions(self, subject: str) -> int:
        count = 0
        now = self._now_provider()
        for record in self._store.list_by_subject(subject):
            if self._store.revoke(record.session_id, revoked_at=now):
                count += 1
        return count


def build_session_store(
    *,
    provider: Literal["memory", "redis"] = "memory",
    redis_url: str | None = None,
    key_prefix: str = "eitohforge:sessions",
) -> SessionStore:
    """Build a session store from provider configuration."""
    if provider == "memory":
        return InMemorySessionStore()
    if provider == "redis":
        if redis_url is None:
            raise ValueError("redis_url is required for redis session store provider.")
        return RedisSessionStore(redis_url=redis_url, key_prefix=key_prefix)
    raise ValueError(f"Unsupported session store provider: {provider}")

