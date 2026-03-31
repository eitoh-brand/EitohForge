from __future__ import annotations

from unittest.mock import MagicMock, patch

from eitohforge_sdk.core.secrets_cloud import GcpSecretManagerSecretProvider


def test_gcp_secret_manager_resolves_short_secret_id() -> None:
    with patch("google.cloud.secretmanager.SecretManagerServiceClient") as ctor:
        mock_client = MagicMock()
        ctor.return_value = mock_client
        mock_client.access_secret_version.return_value.payload.data = b"secret-val"
        p = GcpSecretManagerSecretProvider(project_id="p1")
        assert p.get("foo") == "secret-val"
        req = mock_client.access_secret_version.call_args[1]["request"]
        assert req["name"] == "projects/p1/secrets/foo/versions/latest"


def test_gcp_secret_manager_uses_full_resource_name() -> None:
    with patch("google.cloud.secretmanager.SecretManagerServiceClient") as ctor:
        mock_client = MagicMock()
        ctor.return_value = mock_client
        mock_client.access_secret_version.return_value.payload.data = b"x"
        p = GcpSecretManagerSecretProvider(project_id="ignored")
        full = "projects/p2/secrets/bar/versions/3"
        assert p.get(full) == "x"
        req = mock_client.access_secret_version.call_args[1]["request"]
        assert req["name"] == full


def test_gcp_secret_manager_appends_latest_when_project_path_without_version() -> None:
    with patch("google.cloud.secretmanager.SecretManagerServiceClient") as ctor:
        mock_client = MagicMock()
        ctor.return_value = mock_client
        mock_client.access_secret_version.return_value.payload.data = b"y"
        p = GcpSecretManagerSecretProvider(project_id="p1")
        name = "projects/p1/secrets/baz"
        assert p.get(name) == "y"
        req = mock_client.access_secret_version.call_args[1]["request"]
        assert req["name"] == "projects/p1/secrets/baz/versions/latest"
