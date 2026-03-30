"""Local filesystem storage provider."""

from __future__ import annotations

from pathlib import Path

from eitohforge_sdk.infrastructure.storage.contracts import StorageObject


class LocalStorageProvider:
    """Store objects on local filesystem under a root directory."""

    def __init__(self, *, root_path: Path) -> None:
        self._root_path = root_path.resolve()
        self._root_path.mkdir(parents=True, exist_ok=True)

    def put_bytes(self, key: str, data: bytes, *, content_type: str | None = None) -> StorageObject:
        path = self._resolve_key_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return StorageObject(key=key, size_bytes=len(data), content_type=content_type)

    def get_bytes(self, key: str) -> bytes:
        path = self._resolve_key_path(key)
        return path.read_bytes()

    def delete(self, key: str) -> bool:
        path = self._resolve_key_path(key)
        if not path.exists():
            return False
        path.unlink()
        return True

    def exists(self, key: str) -> bool:
        path = self._resolve_key_path(key)
        return path.exists()

    def _resolve_key_path(self, key: str) -> Path:
        clean_key = key.strip().lstrip("/")
        if not clean_key:
            raise ValueError("Storage key must not be empty.")
        path = (self._root_path / clean_key).resolve()
        if not str(path).startswith(str(self._root_path)):
            raise ValueError("Storage key resolves outside root path.")
        return path

