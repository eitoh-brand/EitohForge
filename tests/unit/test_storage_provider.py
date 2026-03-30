from pathlib import Path
from typing import Any

import pytest

from eitohforge_sdk.core.config import AppSettings
from eitohforge_sdk.infrastructure.storage import (
    LocalStorageProvider,
    S3StorageProvider,
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
    settings = AppSettings()
    provider = build_storage_provider(settings, local_root_path=tmp_path / "storage")
    assert isinstance(provider, LocalStorageProvider)


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
    assert provider.delete("files/a.txt") is True
    assert provider.exists("files/a.txt") is False


def test_build_storage_provider_for_s3_settings() -> None:
    settings = AppSettings(storage={"provider": "s3", "bucket_name": "bucket", "region": "ap-south-1"})
    provider = build_storage_provider(settings, s3_client=_FakeS3Client())
    assert isinstance(provider, S3StorageProvider)

