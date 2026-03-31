"""Storage access policy engine and enforcing provider wrapper."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, cast

from eitohforge_sdk.infrastructure.storage.contracts import (
    PresignableStorageProvider,
    StorageObject,
    StorageProvider,
)


class StorageAction(str, Enum):
    """Storage actions subject to policy checks."""

    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    PRESIGN_GET = "presign_get"
    PRESIGN_PUT = "presign_put"


@dataclass(frozen=True)
class StorageAccessContext:
    """Caller context used during storage authorization checks."""

    actor_id: str | None = None
    tenant_id: str | None = None
    roles: tuple[str, ...] = ()
    permissions: tuple[str, ...] = ()


@dataclass(frozen=True)
class StorageAccessRequest:
    """Storage authorization request."""

    action: StorageAction
    key: str
    context: StorageAccessContext
    metadata: Mapping[str, Any] = field(default_factory=dict)


class StoragePolicyDeniedError(PermissionError):
    """Raised when one or more storage policies deny access."""


class StorageAccessPolicy(Protocol):
    """Storage access policy contract."""

    name: str

    def evaluate(self, request: StorageAccessRequest) -> bool:
        ...


@dataclass(frozen=True)
class AuthenticatedActorPolicy:
    """Allow only requests with an authenticated actor."""

    name: str = "authenticated_actor"

    def evaluate(self, request: StorageAccessRequest) -> bool:
        return request.context.actor_id is not None


@dataclass(frozen=True)
class TenantPrefixPolicy:
    """Require object key prefix to match tenant id."""

    separator: str = "/"
    name: str = "tenant_prefix"

    def evaluate(self, request: StorageAccessRequest) -> bool:
        tenant_id = request.context.tenant_id
        if tenant_id is None:
            return False
        return request.key.startswith(f"{tenant_id}{self.separator}")


@dataclass(frozen=True)
class RoleStorageAccessPolicy:
    """Require role match per storage action."""

    roles_by_action: Mapping[StorageAction, tuple[str, ...]]
    name: str = "role_storage_access"

    def evaluate(self, request: StorageAccessRequest) -> bool:
        required_roles = tuple(
            role.lower() for role in self.roles_by_action.get(request.action, ()) if role.strip()
        )
        if not required_roles:
            return True
        caller_roles = set(role.lower() for role in request.context.roles)
        return any(role in caller_roles for role in required_roles)


class StoragePolicyEngine:
    """Evaluate storage policies for an action request."""

    def evaluate(
        self, request: StorageAccessRequest, policies: tuple[StorageAccessPolicy, ...]
    ) -> tuple[str, ...]:
        return tuple(policy.name for policy in policies if not policy.evaluate(request))

    def assert_allowed(
        self, request: StorageAccessRequest, policies: tuple[StorageAccessPolicy, ...]
    ) -> None:
        denied = self.evaluate(request, policies)
        if denied:
            raise StoragePolicyDeniedError(
                f"Storage access denied by policies: {', '.join(denied)}"
            )


class PolicyEnforcedStorageProvider:
    """Storage provider wrapper that enforces access policies per operation."""

    def __init__(
        self,
        *,
        delegate: StorageProvider,
        context_provider: Callable[[], StorageAccessContext],
        policies: tuple[StorageAccessPolicy, ...],
        policy_engine: StoragePolicyEngine | None = None,
    ) -> None:
        self._delegate = delegate
        self._context_provider = context_provider
        self._policies = policies
        self._policy_engine = policy_engine or StoragePolicyEngine()

    def put_bytes(self, key: str, data: bytes, *, content_type: str | None = None) -> StorageObject:
        self._authorize(StorageAction.WRITE, key, {"content_type": content_type})
        return self._delegate.put_bytes(key, data, content_type=content_type)

    def get_bytes(self, key: str) -> bytes:
        self._authorize(StorageAction.READ, key)
        return self._delegate.get_bytes(key)

    def delete(self, key: str) -> bool:
        self._authorize(StorageAction.DELETE, key)
        return self._delegate.delete(key)

    def exists(self, key: str) -> bool:
        self._authorize(StorageAction.READ, key)
        return self._delegate.exists(key)

    def generate_presigned_get_url(self, key: str, *, expires_in: int) -> str:
        self._authorize(StorageAction.PRESIGN_GET, key, {"expires_in": expires_in})
        delegate = self._as_presignable_delegate()
        return delegate.generate_presigned_get_url(key, expires_in=expires_in)

    def generate_presigned_put_url(
        self, key: str, *, expires_in: int, content_type: str | None = None
    ) -> str:
        self._authorize(
            StorageAction.PRESIGN_PUT,
            key,
            {"expires_in": expires_in, "content_type": content_type},
        )
        delegate = self._as_presignable_delegate()
        return delegate.generate_presigned_put_url(
            key, expires_in=expires_in, content_type=content_type
        )

    def generate_presigned_download(self, key: str, *, expires_in: int) -> str:
        self._authorize(StorageAction.PRESIGN_GET, key, {"expires_in": expires_in})
        delegate = self._as_presignable_delegate()
        return delegate.generate_presigned_download(key, expires_in=expires_in)

    def generate_presigned_upload(
        self, key: str, *, expires_in: int, content_type: str | None = None
    ) -> str:
        self._authorize(
            StorageAction.PRESIGN_PUT,
            key,
            {"expires_in": expires_in, "content_type": content_type},
        )
        delegate = self._as_presignable_delegate()
        return delegate.generate_presigned_upload(
            key, expires_in=expires_in, content_type=content_type
        )

    def generate_public_url(self, key: str) -> str:
        self._authorize(StorageAction.READ, key)
        delegate = self._delegate
        if not hasattr(delegate, "generate_public_url"):
            raise TypeError("Underlying storage provider does not support public object URLs.")
        return delegate.generate_public_url(key)

    def _authorize(self, action: StorageAction, key: str, metadata: Mapping[str, Any] | None = None) -> None:
        request = StorageAccessRequest(
            action=action,
            key=key,
            context=self._context_provider(),
            metadata=metadata or {},
        )
        self._policy_engine.assert_allowed(request, self._policies)

    def _as_presignable_delegate(self) -> PresignableStorageProvider:
        delegate = self._delegate
        if not hasattr(delegate, "generate_presigned_get_url") or not hasattr(
            delegate, "generate_presigned_put_url"
        ):
            raise TypeError("Underlying storage provider does not support presigned URLs.")
        return cast(PresignableStorageProvider, delegate)

