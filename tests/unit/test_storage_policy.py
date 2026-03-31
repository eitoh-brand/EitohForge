from pathlib import Path

import pytest

from eitohforge_sdk.infrastructure.storage import (
    AuthenticatedActorPolicy,
    LocalStorageProvider,
    PolicyEnforcedStorageProvider,
    PresignedObjectUrlsMixin,
    RoleStorageAccessPolicy,
    StorageAccessContext,
    StorageAction,
    StoragePolicyDeniedError,
    TenantPrefixPolicy,
)


class _FakePresignStorageProvider(PresignedObjectUrlsMixin, LocalStorageProvider):
    def generate_presigned_get_url(self, key: str, *, expires_in: int) -> str:
        return f"https://signed/get/{key}?exp={expires_in}"

    def generate_presigned_put_url(
        self, key: str, *, expires_in: int, content_type: str | None = None
    ) -> str:
        suffix = f"&content_type={content_type}" if content_type is not None else ""
        return f"https://signed/put/{key}?exp={expires_in}{suffix}"


def test_policy_enforced_storage_denies_without_actor(tmp_path: Path) -> None:
    provider = PolicyEnforcedStorageProvider(
        delegate=LocalStorageProvider(root_path=tmp_path / "storage"),
        context_provider=lambda: StorageAccessContext(actor_id=None, tenant_id="acme"),
        policies=(AuthenticatedActorPolicy(),),
    )
    with pytest.raises(StoragePolicyDeniedError):
        provider.put_bytes("acme/file.txt", b"x")


def test_policy_enforced_storage_enforces_tenant_prefix(tmp_path: Path) -> None:
    provider = PolicyEnforcedStorageProvider(
        delegate=LocalStorageProvider(root_path=tmp_path / "storage"),
        context_provider=lambda: StorageAccessContext(actor_id="u1", tenant_id="acme"),
        policies=(AuthenticatedActorPolicy(), TenantPrefixPolicy()),
    )
    provider.put_bytes("acme/file.txt", b"ok")
    with pytest.raises(StoragePolicyDeniedError):
        provider.put_bytes("other/file.txt", b"nope")


def test_policy_enforced_storage_enforces_role_by_action(tmp_path: Path) -> None:
    policy = RoleStorageAccessPolicy(roles_by_action={StorageAction.DELETE: ("admin",)})
    provider = PolicyEnforcedStorageProvider(
        delegate=LocalStorageProvider(root_path=tmp_path / "storage"),
        context_provider=lambda: StorageAccessContext(actor_id="u1", tenant_id="acme", roles=("user",)),
        policies=(AuthenticatedActorPolicy(), policy),
    )
    provider.put_bytes("acme/file.txt", b"ok")
    with pytest.raises(StoragePolicyDeniedError):
        provider.delete("acme/file.txt")


def test_policy_enforced_storage_supports_presignable_delegate(tmp_path: Path) -> None:
    provider = PolicyEnforcedStorageProvider(
        delegate=_FakePresignStorageProvider(root_path=tmp_path / "storage"),
        context_provider=lambda: StorageAccessContext(actor_id="u1", tenant_id="acme", roles=("admin",)),
        policies=(AuthenticatedActorPolicy(),),
    )
    url = provider.generate_presigned_put_url(
        "acme/upload.txt", expires_in=120, content_type="text/plain"
    )
    assert "signed/put" in url
    assert "exp=120" in url
    dl = provider.generate_presigned_download("acme/upload.txt", expires_in=30)
    assert "signed/get" in dl
    assert "exp=30" in dl


def test_policy_enforced_generate_public_url_requires_delegate(tmp_path: Path) -> None:
    provider = PolicyEnforcedStorageProvider(
        delegate=LocalStorageProvider(root_path=tmp_path / "storage"),
        context_provider=lambda: StorageAccessContext(actor_id="u1", tenant_id="acme"),
        policies=(AuthenticatedActorPolicy(), TenantPrefixPolicy()),
    )
    with pytest.raises(TypeError):
        provider.generate_public_url("acme/file.txt")

