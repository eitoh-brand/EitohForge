from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from eitohforge_sdk.core.auth import SessionExpiredError, SessionManager, SessionRevokedError


def test_session_manager_create_and_validate_session() -> None:
    manager = SessionManager()
    session = manager.create_session(subject="user-1", tenant_id="tenant-a")

    validated = manager.validate_session(session.session_id)
    assert validated.subject == "user-1"
    assert validated.tenant_id == "tenant-a"


def test_session_manager_revoke_single_session() -> None:
    manager = SessionManager()
    session = manager.create_session(subject="user-1")

    assert manager.revoke_session(session.session_id) is True
    with pytest.raises(SessionRevokedError):
        manager.validate_session(session.session_id)


def test_session_manager_revoke_all_sessions_for_subject() -> None:
    manager = SessionManager()
    s1 = manager.create_session(subject="user-1")
    s2 = manager.create_session(subject="user-1")
    other = manager.create_session(subject="user-2")

    revoked = manager.revoke_all_sessions("user-1")
    assert revoked == 2
    with pytest.raises(SessionRevokedError):
        manager.validate_session(s1.session_id)
    with pytest.raises(SessionRevokedError):
        manager.validate_session(s2.session_id)
    assert manager.validate_session(other.session_id).subject == "user-2"


def test_session_manager_detects_expired_session() -> None:
    now_state = {"now": datetime(2026, 1, 1, tzinfo=UTC)}

    def _now() -> datetime:
        return now_state["now"]

    manager = SessionManager(default_ttl=timedelta(seconds=1), now_provider=_now)
    session = manager.create_session(subject="user-1")
    now_state["now"] = now_state["now"] + timedelta(seconds=2)

    with pytest.raises(SessionExpiredError):
        manager.validate_session(session.session_id)

