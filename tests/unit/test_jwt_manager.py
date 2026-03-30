from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from eitohforge_sdk.core.auth import (
    InvalidTokenError,
    JwtTokenManager,
    RefreshTokenReplayError,
    TokenExpiredError,
    TokenType,
)


def test_jwt_manager_issues_and_validates_token_pair() -> None:
    manager = JwtTokenManager(secret="x" * 32)
    pair = manager.issue_token_pair(subject="user-1", tenant_id="tenant-a")

    access_claims = manager.decode_and_validate(pair.access_token, expected_type=TokenType.ACCESS)
    refresh_claims = manager.decode_and_validate(pair.refresh_token, expected_type=TokenType.REFRESH)
    assert access_claims["sub"] == "user-1"
    assert refresh_claims["tenant_id"] == "tenant-a"


def test_jwt_refresh_rotation_revokes_old_token() -> None:
    manager = JwtTokenManager(secret="x" * 32)
    pair = manager.issue_token_pair(subject="user-1")
    rotated = manager.rotate_refresh_token(pair.refresh_token)

    assert rotated.refresh_token != pair.refresh_token
    with pytest.raises(RefreshTokenReplayError):
        manager.rotate_refresh_token(pair.refresh_token)


def test_jwt_manager_detects_expired_access_token() -> None:
    now_state = {"now": datetime(2026, 1, 1, tzinfo=UTC)}

    def _now() -> datetime:
        return now_state["now"]

    manager = JwtTokenManager(
        secret="x" * 32,
        access_ttl=timedelta(seconds=1),
        refresh_ttl=timedelta(minutes=5),
        now_provider=_now,
    )
    pair = manager.issue_token_pair(subject="user-1")
    now_state["now"] = now_state["now"] + timedelta(seconds=2)

    with pytest.raises(TokenExpiredError):
        manager.decode_and_validate(pair.access_token, expected_type=TokenType.ACCESS)


def test_jwt_manager_rejects_wrong_token_type() -> None:
    manager = JwtTokenManager(secret="x" * 32)
    pair = manager.issue_token_pair(subject="user-1")

    with pytest.raises(InvalidTokenError):
        manager.decode_and_validate(pair.access_token, expected_type=TokenType.REFRESH)

