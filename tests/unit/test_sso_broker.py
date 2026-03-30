from __future__ import annotations

import pytest

from eitohforge_sdk.core.auth import (
    ExternalIdentity,
    InMemorySsoLinkStore,
    JwtTokenManager,
    SessionManager,
    SsoBroker,
    SsoIdentityNotLinkedError,
    SsoProviderNotFoundError,
    TokenType,
)


class FakeGoogleProvider:
    name = "google"

    def exchange_authorization_code(
        self, *, code: str, redirect_uri: str | None = None, state: str | None = None
    ) -> ExternalIdentity:
        _ = (redirect_uri, state)
        return ExternalIdentity(
            provider=self.name,
            subject=f"google-user-{code}",
            email="user@example.com",
            tenant_id="tenant-a",
        )


class FakeGoogleProviderTenantFromCode:
    name = "google"

    def exchange_authorization_code(
        self, *, code: str, redirect_uri: str | None = None, state: str | None = None
    ) -> ExternalIdentity:
        _ = (redirect_uri, state)
        # external subject stays constant while tenant_id changes via `code`
        return ExternalIdentity(
            provider=self.name,
            subject="google-user-constant",
            email="user@example.com",
            tenant_id=code,
        )


def test_sso_broker_authenticates_and_issues_internal_jwt_session() -> None:
    jwt_manager = JwtTokenManager(secret="x" * 32)
    session_manager = SessionManager()
    link_store = InMemorySsoLinkStore()
    link_store.upsert_link(
        provider="google",
        external_subject="google-user-auth-code",
        tenant_id="tenant-a",
        internal_subject="internal-user-42",
    )

    broker = SsoBroker(
        jwt_manager=jwt_manager,
        session_manager=session_manager,
        providers=(FakeGoogleProvider(),),
        link_store=link_store,
    )
    result = broker.authenticate(provider_name="google", code="auth-code")
    claims = jwt_manager.decode_and_validate(result.token_pair.access_token, expected_type=TokenType.ACCESS)

    assert result.internal_subject == "internal-user-42"
    assert result.is_new_link is False
    assert claims["sub"] == "internal-user-42"
    assert claims["auth_provider"] == "google"
    assert claims["external_sub"] == "google-user-auth-code"
    assert session_manager.validate_session(result.session_id).subject == "internal-user-42"


def test_sso_broker_auto_provisions_when_link_missing() -> None:
    broker = SsoBroker(
        jwt_manager=JwtTokenManager(secret="x" * 32),
        session_manager=SessionManager(),
        providers=(FakeGoogleProvider(),),
    )
    result = broker.authenticate(provider_name="google", code="first-login")
    assert result.is_new_link is True
    assert result.internal_subject == "sso:google:tenant-a:google-user-first-login"


def test_sso_broker_rejects_unknown_provider() -> None:
    broker = SsoBroker(
        jwt_manager=JwtTokenManager(secret="x" * 32),
        session_manager=SessionManager(),
    )
    with pytest.raises(SsoProviderNotFoundError):
        broker.authenticate(provider_name="unknown", code="x")


def test_sso_broker_rejects_unlinked_identity_when_autoprovision_disabled() -> None:
    broker = SsoBroker(
        jwt_manager=JwtTokenManager(secret="x" * 32),
        session_manager=SessionManager(),
        providers=(FakeGoogleProvider(),),
        auto_provision=False,
    )
    with pytest.raises(SsoIdentityNotLinkedError):
        broker.authenticate(provider_name="google", code="new-user")


def test_sso_broker_links_are_isolated_by_tenant() -> None:
    jwt_manager = JwtTokenManager(secret="x" * 32)
    session_manager = SessionManager()

    link_store = InMemorySsoLinkStore()
    link_store.upsert_link(
        provider="google",
        external_subject="google-user-constant",
        tenant_id="tenant-a",
        internal_subject="internal-user-tenant-a",
    )

    broker = SsoBroker(
        jwt_manager=jwt_manager,
        session_manager=session_manager,
        providers=(FakeGoogleProviderTenantFromCode(),),
        link_store=link_store,
        auto_provision=True,
    )

    # Tenant A finds the pre-upserted link.
    result_a = broker.authenticate(provider_name="google", code="tenant-a")
    assert result_a.is_new_link is False
    assert result_a.internal_subject == "internal-user-tenant-a"
    assert session_manager.validate_session(result_a.session_id).tenant_id == "tenant-a"

    # Tenant B should not see Tenant A's link.
    result_b = broker.authenticate(provider_name="google", code="tenant-b")
    assert result_b.is_new_link is True
    assert result_b.internal_subject == "sso:google:tenant-b:google-user-constant"
    assert session_manager.validate_session(result_b.session_id).tenant_id == "tenant-b"
