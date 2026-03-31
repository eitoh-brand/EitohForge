"""Exercise optional cloud storage import paths (no real cloud calls)."""

from __future__ import annotations

import importlib

import pytest

from eitohforge_sdk.core.config import StorageSettings
from eitohforge_sdk.infrastructure.storage.factory import _build_storage_provider_for_settings


def test_azure_parse_connection_string_requires_keys() -> None:
    az_mod = importlib.import_module("eitohforge_sdk.infrastructure.storage.azure_blob")
    with pytest.raises(ValueError, match="AccountName"):
        az_mod._account_name_key_from_connection_string("Invalid=only")


def test_gcs_generate_public_url_uses_configured_cdn_base() -> None:
    gcs_mod = importlib.import_module("eitohforge_sdk.infrastructure.storage.gcs")

    class _B:
        name = "bk"

    class _C:
        def bucket(self, name: str) -> _B:
            return _B()

    provider = gcs_mod.GcsStorageProvider(
        bucket_name="bk",
        public_base_url="https://cdn.example/assets",
        client=_C(),
    )
    assert provider.generate_public_url("dir/f.png") == "https://cdn.example/assets/dir/f.png"


def test_build_gcs_factory_with_injected_client(monkeypatch: pytest.MonkeyPatch) -> None:
    gcs_mod = importlib.import_module("eitohforge_sdk.infrastructure.storage.gcs")

    class _FakeBucket:
        def __init__(self, name: str) -> None:
            self.name = name

    class _FakeClient:
        def bucket(self, name: str) -> _FakeBucket:
            return _FakeBucket(name)

    monkeypatch.setattr(gcs_mod, "_storage_client", lambda project: _FakeClient())
    provider = _build_storage_provider_for_settings(
        StorageSettings(provider="gcs", bucket_name="my-bucket"),
        local_root_path=None,
        s3_client=None,
    )
    assert isinstance(provider, gcs_mod.GcsStorageProvider)


def test_gcs_storage_client_raises_without_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    gcs_mod = importlib.import_module("eitohforge_sdk.infrastructure.storage.gcs")
    real_import = importlib.import_module

    def fake_import(name: str, *args: object, **kwargs: object):
        if name == "google.cloud.storage":
            raise ModuleNotFoundError("google.cloud.storage")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(gcs_mod.importlib, "import_module", fake_import)
    with pytest.raises(RuntimeError, match="google-cloud-storage"):
        gcs_mod._storage_client(project=None)


def test_azure_blob_types_raises_without_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    az_mod = importlib.import_module("eitohforge_sdk.infrastructure.storage.azure_blob")
    real_import = importlib.import_module

    def fake_import(name: str, *args: object, **kwargs: object):
        if name == "azure.storage.blob":
            raise ModuleNotFoundError("azure.storage.blob")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(az_mod.importlib, "import_module", fake_import)
    with pytest.raises(RuntimeError, match="azure-storage-blob"):
        az_mod._azure_blob_types()


def test_azure_blob_provider_with_mocks(monkeypatch: pytest.MonkeyPatch) -> None:
    az_mod = importlib.import_module("eitohforge_sdk.infrastructure.storage.azure_blob")

    class _ContentSettings:
        def __init__(self, content_type: str | None = None) -> None:
            self.content_type = content_type

    class _BlobClient:
        def __init__(self) -> None:
            self.url = "https://acct.blob.core.windows.net/c/k"

        def upload_blob(self, data: bytes, overwrite: bool = True, **kwargs: object) -> None:
            pass

        def download_blob(self) -> object:
            class _DL:
                def readall(self) -> bytes:
                    return b"payload"

            return _DL()

        def delete_blob(self) -> None:
            pass

        def exists(self) -> bool:
            return True

    class _ContainerClient:
        def get_blob_client(self, key: str) -> _BlobClient:
            return _BlobClient()

    class _Service:
        def get_container_client(self, name: str) -> _ContainerClient:
            return _ContainerClient()

    class _BlobServiceClient:
        @staticmethod
        def from_connection_string(conn: str) -> _Service:
            return _Service()

    def _fake_generate_blob_sas(**kwargs: object) -> str:
        return "sas=fake"

    class _BlobSasPermissions:
        def __init__(self, **kwargs: object) -> None:
            pass

    monkeypatch.setattr(
        az_mod,
        "_azure_blob_types",
        lambda: (_BlobServiceClient, _fake_generate_blob_sas, _BlobSasPermissions, _ContentSettings),
    )

    conn = "AccountName=a;AccountKey=k;EndpointSuffix=core.windows.net"
    provider = az_mod.AzureBlobStorageProvider(
        connection_string=conn,
        container_name="c",
        public_base_url="https://cdn.example/prefix/",
    )
    obj = provider.put_bytes("key1", b"ab", content_type="application/octet-stream")
    assert obj.size_bytes == 2
    assert provider.get_bytes("key1") == b"payload"
    assert provider.delete("key1") is True
    assert provider.exists("key1") is True
    get_url = provider.generate_presigned_get_url("key1", expires_in=120)
    assert "sas=fake" in get_url
    put_url = provider.generate_presigned_put_url("key2", expires_in=60, content_type="text/plain")
    assert "sas=fake" in put_url
    assert provider.generate_public_url("a/b") == "https://cdn.example/prefix/a/b"


def test_azure_blob_delete_returns_false_when_blob_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    az_mod = importlib.import_module("eitohforge_sdk.infrastructure.storage.azure_blob")

    class _BlobClient:
        def delete_blob(self) -> None:
            raise RuntimeError("gone")

    class _ContainerClient:
        def get_blob_client(self, key: str) -> _BlobClient:
            return _BlobClient()

    class _Service:
        def get_container_client(self, name: str) -> _ContainerClient:
            return _ContainerClient()

    class _BlobServiceClient:
        @staticmethod
        def from_connection_string(conn: str) -> _Service:
            return _Service()

    class _DummyPerm:
        def __init__(self, **kwargs: object) -> None:
            pass

    class _DummyContent:
        def __init__(self, content_type: str | None = None) -> None:
            pass

    monkeypatch.setattr(
        az_mod,
        "_azure_blob_types",
        lambda: (_BlobServiceClient, lambda **k: "", _DummyPerm, _DummyContent),
    )

    conn = "AccountName=a;AccountKey=k;"
    provider = az_mod.AzureBlobStorageProvider(connection_string=conn, container_name="c")
    assert provider.delete("x") is False


def test_gcs_provider_methods_with_mocks() -> None:
    gcs_mod = importlib.import_module("eitohforge_sdk.infrastructure.storage.gcs")

    class _Blob:
        def upload_from_string(self, data: bytes, content_type: str | None = None) -> None:
            pass

        def download_as_bytes(self) -> bytes:
            return b"ok"

        def delete(self) -> None:
            pass

        def exists(self) -> bool:
            return True

        def generate_signed_url(self, **kwargs: object) -> str:
            return "https://signed.example/get"

    class _Bucket:
        name = "mybucket"

        def blob(self, key: str) -> _Blob:
            return _Blob()

    class _Client:
        def bucket(self, name: str) -> _Bucket:
            return _Bucket()

    provider = gcs_mod.GcsStorageProvider(bucket_name="mybucket", client=_Client())
    provider.put_bytes("a", b"x", content_type="text/plain")
    assert provider.get_bytes("a") == b"ok"
    assert provider.delete("a") is True
    assert provider.exists("a") is True
    assert "signed.example" in provider.generate_presigned_get_url("a", expires_in=30)
    assert "signed.example" in provider.generate_presigned_put_url(
        "a", expires_in=30, content_type="image/png"
    )
    pub = provider.generate_public_url("dir/obj")
    assert "storage.googleapis.com" in pub
    assert "mybucket" in pub


def test_gcs_delete_returns_false_when_blob_raises() -> None:
    gcs_mod = importlib.import_module("eitohforge_sdk.infrastructure.storage.gcs")

    class _Blob:
        def delete(self) -> None:
            raise RuntimeError("missing")

    class _Bucket:
        name = "b"

        def blob(self, key: str) -> _Blob:
            return _Blob()

    class _Client:
        def bucket(self, name: str) -> _Bucket:
            return _Bucket()

    provider = gcs_mod.GcsStorageProvider(bucket_name="b", client=_Client())
    assert provider.delete("k") is False
