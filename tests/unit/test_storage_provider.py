from pathlib import Path
from typing import Any

import shutil
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from eitohforge_sdk.core.config import AppSettings
from eitohforge_sdk.core.tenant import TenantIsolationRule, register_tenant_context_middleware
from eitohforge_sdk.infrastructure.storage import (
    LocalStorageProvider,
    S3StorageProvider,
    TenantScopedStorageProvider,
    build_storage_provider,
)


def test_local_storage_provider_put_get_delete(tmp_path: Path) -> None:
    provider = LocalStorageProvider(root_path=tmp_path / "storage")
    result = provider.put_bytes("images/avatar.png", b"binary-data", content_type="image/png")
    assert result.key == "images/avatar.png"
    assert result.size_bytes == 11
    assert result.content_type == "image/png"
    assert provider.exists("images/avatar.png")
    assert provider.get_bytes("images/avatar.png") == b"binary-data"
    assert provider.delete("images/avatar.png") is True
    assert provider.exists("images/avatar.png") is False
    assert provider.delete("images/avatar.png") is False


def test_local_storage_provider_rejects_path_traversal(tmp_path: Path) -> None:
    provider = LocalStorageProvider(root_path=tmp_path / "storage")
    with pytest.raises(ValueError):
        provider.put_bytes("../outside.txt", b"x")


def test_build_storage_provider_from_settings(tmp_path: Path) -> None:
    settings = AppSettings(tenant={"enabled": False})
    provider = build_storage_provider(settings, local_root_path=tmp_path / "storage")
    assert isinstance(provider, LocalStorageProvider)


def test_build_storage_provider_minio_uses_s3_adapter(tmp_path: Path) -> None:
    settings = AppSettings(
        tenant={"enabled": False},
        storage={
            "provider": "minio",
            "bucket_name": "files",
            "region": "us-east-1",
            "endpoint_url": "http://127.0.0.1:9000",
        },
    )
    provider = build_storage_provider(settings, s3_client=object())
    from eitohforge_sdk.infrastructure.storage import S3StorageProvider

    assert isinstance(provider, S3StorageProvider)


def test_build_storage_provider_azure_requires_connection_string(tmp_path: Path) -> None:
    settings = AppSettings(
        tenant={"enabled": False},
        storage={"provider": "azure", "bucket_name": "container1"},
    )
    with pytest.raises(ValueError, match="Azure"):
        build_storage_provider(settings, local_root_path=tmp_path / "storage")


class _FakeS3Body:
    def __init__(self, data: bytes) -> None:
        self._data = data

    def read(self) -> bytes:
        return self._data


class _FakeS3Client:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.last_presign: dict[str, Any] = {}

    def put_object(self, **kwargs: Any) -> None:
        self.objects[str(kwargs["Key"])] = bytes(kwargs["Body"])

    def get_object(self, **kwargs: Any) -> dict[str, Any]:
        key = str(kwargs["Key"])
        return {"Body": _FakeS3Body(self.objects[key])}

    def delete_object(self, **kwargs: Any) -> None:
        key = str(kwargs["Key"])
        self.objects.pop(key, None)

    def head_object(self, **kwargs: Any) -> None:
        key = str(kwargs["Key"])
        if key not in self.objects:
            error = Exception("not found")
            error.response = {"Error": {"Code": "404"}}  # type: ignore[attr-defined]
            raise error

    def generate_presigned_url(self, operation_name: str, *, Params: dict[str, Any], ExpiresIn: int) -> str:
        self.last_presign = {
            "operation_name": operation_name,
            "params": Params,
            "expires_in": ExpiresIn,
        }
        return f"https://signed.example/{operation_name}/{Params['Key']}?exp={ExpiresIn}"


def test_s3_storage_provider_supports_presigned_urls() -> None:
    client = _FakeS3Client()
    provider = S3StorageProvider(bucket_name="bucket", region="us-east-1", client=client)
    result = provider.put_bytes("files/a.txt", b"hello", content_type="text/plain")
    assert result.size_bytes == 5
    assert provider.exists("files/a.txt") is True
    assert provider.get_bytes("files/a.txt") == b"hello"
    put_url = provider.generate_presigned_put_url(
        "files/upload.txt", expires_in=300, content_type="text/plain"
    )
    assert "put_object" in put_url
    get_url = provider.generate_presigned_get_url("files/a.txt", expires_in=60)
    assert "get_object" in get_url
    assert provider.generate_presigned_upload(
        "files/upload.txt", expires_in=300, content_type="text/plain"
    ) == put_url
    assert provider.generate_presigned_download("files/a.txt", expires_in=60) == get_url
    assert (
        provider.generate_public_url("files/a.txt")
        == "https://bucket.s3.us-east-1.amazonaws.com/files/a.txt"
    )
    assert provider.delete("files/a.txt") is True
    assert provider.exists("files/a.txt") is False


def test_s3_storage_provider_public_url_uses_explicit_base() -> None:
    client = _FakeS3Client()
    provider = S3StorageProvider(
        bucket_name="bucket",
        region="us-east-1",
        client=client,
        public_base_url="https://cdn.example/assets",
    )
    assert provider.generate_public_url("k.png") == "https://cdn.example/assets/k.png"


def test_build_storage_provider_for_s3_settings() -> None:
    settings = AppSettings(
        tenant={"enabled": False},
        storage={"provider": "s3", "bucket_name": "bucket", "region": "ap-south-1"},
    )
    provider = build_storage_provider(settings, s3_client=_FakeS3Client())
    assert isinstance(provider, S3StorageProvider)


def test_tenant_scoped_storage_provider_prefixes_keys(tmp_path: Path) -> None:
    storage_root = tmp_path / "storage"
    delegate = LocalStorageProvider(root_path=storage_root)
    provider = TenantScopedStorageProvider(delegate=delegate)

    app = FastAPI()
    register_tenant_context_middleware(app, TenantIsolationRule(required_for_write_methods=False))

    @app.post("/put")
    def put() -> dict[str, object]:
        result = provider.put_bytes("files/a.txt", b"hello")
        return {
            "returned_key": result.key,
            "exists_prefixed": delegate.exists(result.key),
            "exists_unprefixed": delegate.exists("files/a.txt"),
        }

    client = TestClient(app)

    resp = client.post("/put", headers={"x-tenant-id": "tenant-a"})
    assert resp.status_code == 200
    assert resp.json()["returned_key"] == "tenant-a/files/a.txt"
    assert resp.json()["exists_prefixed"] is True
    assert resp.json()["exists_unprefixed"] is False

    # Clear between requests so we can assert the unprefixed behavior.
    shutil.rmtree(storage_root)
    storage_root.mkdir(parents=True, exist_ok=True)
    delegate = LocalStorageProvider(root_path=storage_root)
    provider = TenantScopedStorageProvider(delegate=delegate)

    resp = client.post("/put")
    assert resp.status_code == 200
    assert resp.json()["returned_key"] == "files/a.txt"
    assert resp.json()["exists_prefixed"] is True
    assert resp.json()["exists_unprefixed"] is True


def test_tenant_scoped_storage_provider_prefixes_presigned_urls() -> None:
    class _FakePresignStorageProvider:
        def __init__(self) -> None:
            self.last_put_key: str | None = None

        def put_bytes(self, key: str, data: bytes, *, content_type: str | None = None):
            _ = (data, content_type)
            raise NotImplementedError

        def get_bytes(self, key: str) -> bytes:
            raise NotImplementedError

        def delete(self, key: str) -> bool:
            raise NotImplementedError

        def exists(self, key: str) -> bool:
            raise NotImplementedError

        def generate_presigned_get_url(self, key: str, *, expires_in: int) -> str:
            return f"https://signed/get/{key}?exp={expires_in}"

        def generate_presigned_put_url(
            self, key: str, *, expires_in: int, content_type: str | None = None
        ) -> str:
            self.last_put_key = key
            return f"https://signed/put/{key}?exp={expires_in}&ct={content_type}"

    delegate = _FakePresignStorageProvider()
    provider = TenantScopedStorageProvider(delegate=delegate)  # type: ignore[arg-type]

    app = FastAPI()
    register_tenant_context_middleware(app, TenantIsolationRule(required_for_write_methods=False))

    @app.get("/presign")
    def presign() -> dict[str, object]:
        url = provider.generate_presigned_put_url("files/upload.txt", expires_in=10, content_type="text/plain")
        return {"url": url, "last_put_key": delegate.last_put_key}

    client = TestClient(app)
    resp = client.get("/presign", headers={"x-tenant-id": "tenant-a"})
    assert resp.status_code == 200
    assert resp.json()["last_put_key"] == "tenant-a/files/upload.txt"
    assert "tenant-a/files/upload.txt" in resp.json()["url"]

