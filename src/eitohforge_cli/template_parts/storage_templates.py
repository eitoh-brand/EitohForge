"""Storage-layer scaffold template fragments."""

STORAGE_FILE_TEMPLATES: dict[str, str] = {
    "app/infrastructure/storage/__init__.py": """from app.infrastructure.storage.contracts import PresignableStorageProvider, StorageObject, StorageProvider
from app.infrastructure.storage.cdn import CdnUrlRewriter, build_storage_public_url
from app.infrastructure.storage.factory import build_storage_provider
from app.infrastructure.storage.local import LocalStorageProvider
from app.infrastructure.storage.policy import (
    AuthenticatedActorPolicy,
    PolicyEnforcedStorageProvider,
    RoleStorageAccessPolicy,
    StorageAccessContext,
    StorageAccessPolicy,
    StorageAccessRequest,
    StorageAction,
    StoragePolicyDeniedError,
    StoragePolicyEngine,
    TenantPrefixPolicy,
)
from app.infrastructure.storage.s3 import S3StorageProvider
""",
    "app/infrastructure/storage/contracts.py": """from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class StorageObject:
    key: str
    size_bytes: int
    content_type: str | None = None


class StorageProvider(Protocol):
    def put_bytes(self, key: str, data: bytes, *, content_type: str | None = None) -> StorageObject:
        ...

    def get_bytes(self, key: str) -> bytes:
        ...

    def delete(self, key: str) -> bool:
        ...

    def exists(self, key: str) -> bool:
        ...


class PresignableStorageProvider(StorageProvider, Protocol):
    def generate_presigned_get_url(self, key: str, *, expires_in: int) -> str:
        ...

    def generate_presigned_put_url(
        self, key: str, *, expires_in: int, content_type: str | None = None
    ) -> str:
        ...
""",
    "app/infrastructure/storage/local.py": """from pathlib import Path

from app.infrastructure.storage.contracts import StorageObject


class LocalStorageProvider:
    def __init__(self, *, root_path: Path) -> None:
        self._root_path = root_path.resolve()
        self._root_path.mkdir(parents=True, exist_ok=True)

    def put_bytes(self, key: str, data: bytes, *, content_type: str | None = None) -> StorageObject:
        path = self._resolve_key_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return StorageObject(key=key, size_bytes=len(data), content_type=content_type)

    def get_bytes(self, key: str) -> bytes:
        return self._resolve_key_path(key).read_bytes()

    def delete(self, key: str) -> bool:
        path = self._resolve_key_path(key)
        if not path.exists():
            return False
        path.unlink()
        return True

    def exists(self, key: str) -> bool:
        return self._resolve_key_path(key).exists()

    def _resolve_key_path(self, key: str) -> Path:
        clean_key = key.strip().lstrip("/")
        if not clean_key:
            raise ValueError("Storage key must not be empty.")
        path = (self._root_path / clean_key).resolve()
        if not str(path).startswith(str(self._root_path)):
            raise ValueError("Storage key resolves outside root path.")
        return path
""",
    "app/infrastructure/storage/s3.py": """from __future__ import annotations

import importlib
from typing import Any

from app.infrastructure.storage.contracts import StorageObject


class S3StorageProvider:
    def __init__(
        self,
        *,
        bucket_name: str,
        region: str,
        endpoint_url: str | None = None,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        aws_session_token: str | None = None,
        client: Any | None = None,
    ) -> None:
        self._bucket_name = bucket_name
        self._client = client or self._build_client(
            region=region,
            endpoint_url=endpoint_url,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=aws_session_token,
        )

    def put_bytes(self, key: str, data: bytes, *, content_type: str | None = None) -> StorageObject:
        kwargs: dict[str, Any] = {"Bucket": self._bucket_name, "Key": key, "Body": data}
        if content_type is not None:
            kwargs["ContentType"] = content_type
        self._client.put_object(**kwargs)
        return StorageObject(key=key, size_bytes=len(data), content_type=content_type)

    def get_bytes(self, key: str) -> bytes:
        response = self._client.get_object(Bucket=self._bucket_name, Key=key)
        body = response["Body"].read()
        if not isinstance(body, bytes):
            raise TypeError("S3 get_object body must be bytes.")
        return body

    def delete(self, key: str) -> bool:
        self._client.delete_object(Bucket=self._bucket_name, Key=key)
        return True

    def exists(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self._bucket_name, Key=key)
        except Exception as exc:
            error_code = _extract_error_code(exc)
            if error_code in {"404", "NotFound", "NoSuchKey"}:
                return False
            raise
        return True

    def generate_presigned_get_url(self, key: str, *, expires_in: int) -> str:
        return str(
            self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket_name, "Key": key},
                ExpiresIn=expires_in,
            )
        )

    def generate_presigned_put_url(
        self, key: str, *, expires_in: int, content_type: str | None = None
    ) -> str:
        params: dict[str, Any] = {"Bucket": self._bucket_name, "Key": key}
        if content_type is not None:
            params["ContentType"] = content_type
        return str(
            self._client.generate_presigned_url(
                "put_object",
                Params=params,
                ExpiresIn=expires_in,
            )
        )

    @staticmethod
    def _build_client(
        *,
        region: str,
        endpoint_url: str | None,
        aws_access_key_id: str | None,
        aws_secret_access_key: str | None,
        aws_session_token: str | None,
    ) -> Any:
        try:
            boto3 = importlib.import_module("boto3")
        except ModuleNotFoundError as exc:
            raise RuntimeError("S3 storage provider requires 'boto3'. Install via `pip install boto3`.") from exc
        return boto3.client(
            "s3",
            region_name=region,
            endpoint_url=endpoint_url,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=aws_session_token,
        )


def _extract_error_code(error: Exception) -> str | None:
    response = getattr(error, "response", None)
    if not isinstance(response, dict):
        return None
    error_info = response.get("Error")
    if not isinstance(error_info, dict):
        return None
    code = error_info.get("Code")
    return str(code) if code is not None else None
""",
    "app/infrastructure/storage/policy.py": """from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, cast

from app.infrastructure.storage.contracts import PresignableStorageProvider, StorageObject, StorageProvider


class StorageAction(str, Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    PRESIGN_GET = "presign_get"
    PRESIGN_PUT = "presign_put"


@dataclass(frozen=True)
class StorageAccessContext:
    actor_id: str | None = None
    tenant_id: str | None = None
    roles: tuple[str, ...] = ()
    permissions: tuple[str, ...] = ()


@dataclass(frozen=True)
class StorageAccessRequest:
    action: StorageAction
    key: str
    context: StorageAccessContext
    metadata: Mapping[str, Any] = field(default_factory=dict)


class StoragePolicyDeniedError(PermissionError):
    pass


class StorageAccessPolicy(Protocol):
    name: str

    def evaluate(self, request: StorageAccessRequest) -> bool:
        ...


@dataclass(frozen=True)
class AuthenticatedActorPolicy:
    name: str = "authenticated_actor"

    def evaluate(self, request: StorageAccessRequest) -> bool:
        return request.context.actor_id is not None


@dataclass(frozen=True)
class TenantPrefixPolicy:
    separator: str = "/"
    name: str = "tenant_prefix"

    def evaluate(self, request: StorageAccessRequest) -> bool:
        tenant_id = request.context.tenant_id
        if tenant_id is None:
            return False
        return request.key.startswith(f"{tenant_id}{self.separator}")


@dataclass(frozen=True)
class RoleStorageAccessPolicy:
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
    def evaluate(
        self, request: StorageAccessRequest, policies: tuple[StorageAccessPolicy, ...]
    ) -> tuple[str, ...]:
        return tuple(policy.name for policy in policies if not policy.evaluate(request))

    def assert_allowed(
        self, request: StorageAccessRequest, policies: tuple[StorageAccessPolicy, ...]
    ) -> None:
        denied = self.evaluate(request, policies)
        if denied:
            raise StoragePolicyDeniedError(f"Storage access denied by policies: {', '.join(denied)}")


class PolicyEnforcedStorageProvider:
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
        return delegate.generate_presigned_put_url(key, expires_in=expires_in, content_type=content_type)

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
""",
    "app/infrastructure/storage/cdn.py": """from urllib.parse import urlsplit, urlunsplit

from app.core.config import StorageSettings


class CdnUrlRewriter:
    def __init__(self, *, origin_base_url: str, cdn_base_url: str | None = None) -> None:
        self._origin_base_url = _normalize_base_url(origin_base_url)
        self._cdn_base_url = _normalize_base_url(cdn_base_url) if cdn_base_url else None

    def build_public_url(self, key: str) -> str:
        return f"{self._origin_base_url}/{_normalize_key(key)}"

    def rewrite(self, public_url: str) -> str:
        if self._cdn_base_url is None:
            return public_url
        if not public_url.startswith(self._origin_base_url):
            return public_url
        suffix = public_url[len(self._origin_base_url) :]
        return f"{self._cdn_base_url}{suffix}"

    def build_cdn_url(self, key: str) -> str:
        return self.rewrite(self.build_public_url(key))


def build_storage_public_url(key: str, settings: StorageSettings) -> str:
    origin_base_url = _resolve_origin_base_url(settings)
    rewriter = CdnUrlRewriter(origin_base_url=origin_base_url, cdn_base_url=settings.cdn_base_url)
    return rewriter.build_cdn_url(key)


def _resolve_origin_base_url(settings: StorageSettings) -> str:
    if settings.public_base_url:
        return settings.public_base_url
    provider = settings.provider.lower()
    if provider == "s3":
        if settings.endpoint_url:
            endpoint = _normalize_base_url(settings.endpoint_url)
            return f"{endpoint}/{settings.bucket_name}"
        return f"https://{settings.bucket_name}.s3.{settings.region}.amazonaws.com"
    return "http://localhost/storage"


def _normalize_base_url(value: str) -> str:
    parsed = urlsplit(value.strip())
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"Invalid absolute URL: {value}")
    path = parsed.path.rstrip("/")
    return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))


def _normalize_key(key: str) -> str:
    normalized = key.strip().lstrip("/")
    if not normalized:
        raise ValueError("Storage key must not be empty.")
    return normalized
""",
    "app/infrastructure/storage/factory.py": """from pathlib import Path
from typing import Any

from app.core.config import AppSettings, StorageSettings
from app.core.tenant import TenantContext
from app.infrastructure.storage.contracts import StorageProvider
from app.infrastructure.storage.local import LocalStorageProvider
from app.infrastructure.storage.s3 import S3StorageProvider


class TenantScopedStorageProvider:
    def __init__(self, *, delegate: StorageProvider, separator: str = "/") -> None:
        self._delegate = delegate
        self._separator = separator

    def _tenant_id_prefix(self) -> str | None:
        tenant_id = TenantContext.current().tenant_id
        if tenant_id is None:
            return None
        tenant_id = tenant_id.strip()
        if not tenant_id:
            return None
        return f"{tenant_id}{self._separator}"

    def _namespaced_key(self, key: str) -> str:
        prefix = self._tenant_id_prefix()
        if prefix is None:
            return key
        clean_key = key.strip().lstrip("/")
        if not clean_key:
            return key
        if clean_key.startswith(prefix):
            return key
        return f"{prefix}{clean_key}"

    def put_bytes(self, key: str, data: bytes, *, content_type: str | None = None):
        namespaced = self._namespaced_key(key)
        return self._delegate.put_bytes(namespaced, data, content_type=content_type)

    def get_bytes(self, key: str) -> bytes:
        return self._delegate.get_bytes(self._namespaced_key(key))

    def delete(self, key: str) -> bool:
        return self._delegate.delete(self._namespaced_key(key))

    def exists(self, key: str) -> bool:
        return self._delegate.exists(self._namespaced_key(key))

    def _as_presignable_delegate(self) -> StorageProvider:
        if not hasattr(self._delegate, "generate_presigned_get_url") or not hasattr(
            self._delegate, "generate_presigned_put_url"
        ):
            raise TypeError("Underlying storage provider does not support presigned URLs.")
        return self._delegate

    def generate_presigned_get_url(self, key: str, *, expires_in: int) -> str:
        delegate = self._as_presignable_delegate()
        return delegate.generate_presigned_get_url(self._namespaced_key(key), expires_in=expires_in)

    def generate_presigned_put_url(
        self, key: str, *, expires_in: int, content_type: str | None = None
    ) -> str:
        delegate = self._as_presignable_delegate()
        return delegate.generate_presigned_put_url(
            self._namespaced_key(key), expires_in=expires_in, content_type=content_type
        )


def build_storage_provider(
    settings: AppSettings,
    *,
    local_root_path: Path | None = None,
    s3_client: Any | None = None,
) -> StorageProvider:
    delegate = _build_storage_provider_for_settings(
        settings.storage,
        local_root_path=local_root_path,
        s3_client=s3_client,
    )
    if settings.tenant.enabled:
        return TenantScopedStorageProvider(delegate=delegate)
    return delegate


def _build_storage_provider_for_settings(
    settings: StorageSettings, *, local_root_path: Path | None, s3_client: Any | None
) -> StorageProvider:
    provider = settings.provider.lower()
    if provider == "local":
        root_path = local_root_path or Path(".eitohforge/storage")
        return LocalStorageProvider(root_path=root_path)
    if provider == "s3":
        return S3StorageProvider(
            bucket_name=settings.bucket_name,
            region=settings.region,
            endpoint_url=settings.endpoint_url,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            aws_session_token=settings.aws_session_token,
            client=s3_client,
        )
    raise ValueError(f"Unsupported storage provider: {settings.provider}")
""",
}

