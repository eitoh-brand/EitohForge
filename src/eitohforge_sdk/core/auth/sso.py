"""SSO broker and provider contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from eitohforge_sdk.core.auth.jwt import JwtTokenManager, TokenPair
from eitohforge_sdk.core.auth.session import SessionManager


@dataclass(frozen=True)
class ExternalIdentity:
    """Identity asserted by an external SSO provider."""

    provider: str
    subject: str
    email: str | None = None
    display_name: str | None = None
    tenant_id: str | None = None
    claims: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SsoLoginResult:
    """Result of successful SSO exchange into internal credentials."""

    provider: str
    external_subject: str
    internal_subject: str
    token_pair: TokenPair
    session_id: str
    is_new_link: bool


class SsoError(ValueError):
    """Base SSO broker error."""


class SsoProviderNotFoundError(SsoError):
    """Raised when an SSO provider is not registered."""


class SsoIdentityNotLinkedError(SsoError):
    """Raised when external identity has no internal account mapping."""


class SsoProvider(Protocol):
    """External SSO provider contract."""

    name: str

    def exchange_authorization_code(
        self, *, code: str, redirect_uri: str | None = None, state: str | None = None
    ) -> ExternalIdentity:
        ...


class SsoLinkStore(Protocol):
    """Persistent mapping store between external and internal identity."""

    def resolve_subject(
        self, *, provider: str, external_subject: str, tenant_id: str | None
    ) -> str | None:
        ...

    def upsert_link(
        self,
        *,
        provider: str,
        external_subject: str,
        tenant_id: str | None,
        internal_subject: str,
    ) -> None:
        ...


@dataclass
class InMemorySsoLinkStore:
    """In-memory implementation of SSO link mapping."""

    _links: dict[tuple[str, str, str], str] = field(default_factory=dict)

    def resolve_subject(
        self, *, provider: str, external_subject: str, tenant_id: str | None
    ) -> str | None:
        tenant_key = tenant_id or ""
        return self._links.get((provider.strip().lower(), tenant_key, external_subject))

    def upsert_link(
        self,
        *,
        provider: str,
        external_subject: str,
        tenant_id: str | None,
        internal_subject: str,
    ) -> None:
        tenant_key = tenant_id or ""
        self._links[(provider.strip().lower(), tenant_key, external_subject)] = internal_subject


@dataclass
class SsoBroker:
    """Broker that exchanges external SSO identity for internal JWT/session."""

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
            provider=provider_key, external_subject=identity.subject, tenant_id=identity.tenant_id
        )

        is_new_link = False
        if internal_subject is None:
            if not self.auto_provision:
                raise SsoIdentityNotLinkedError(
                    f"No internal account link for provider='{provider_key}' subject='{identity.subject}'."
                )
            if identity.tenant_id:
                internal_subject = f"sso:{provider_key}:{identity.tenant_id}:{identity.subject}"
            else:
                internal_subject = f"sso:{provider_key}:{identity.subject}"
            self.link_store.upsert_link(
                provider=provider_key,
                external_subject=identity.subject,
                tenant_id=identity.tenant_id,
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
