"""S3-compatible storage provider."""

from __future__ import annotations

import importlib
from typing import Any

from eitohforge_sdk.infrastructure.storage.cdn import resolve_s3_origin_base_url
from eitohforge_sdk.infrastructure.storage.contracts import StorageObject
from eitohforge_sdk.infrastructure.storage.presigned_urls import PresignedObjectUrlsMixin


class S3StorageProvider(PresignedObjectUrlsMixin):
    """Store objects in an S3-compatible bucket."""

    def __init__(
        self,
        *,
        bucket_name: str,
        region: str,
        endpoint_url: str | None = None,
        public_base_url: str | None = None,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        aws_session_token: str | None = None,
        client: Any | None = None,
    ) -> None:
        self._bucket_name = bucket_name
        self._region = region
        self._endpoint_url = endpoint_url
        self._public_base_url = public_base_url.rstrip("/") if public_base_url else None
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

    def generate_public_url(self, key: str) -> str:
        """Stable HTTPS URL for the object (not presigned); optional CDN still via ``build_storage_public_url``."""
        base = self._public_base_url or resolve_s3_origin_base_url(
            bucket_name=self._bucket_name,
            region=self._region,
            endpoint_url=self._endpoint_url,
        )
        normalized = key.strip().lstrip("/")
        if not normalized:
            raise ValueError("Storage key must not be empty.")
        return f"{base}/{normalized}"

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

