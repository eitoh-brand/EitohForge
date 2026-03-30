from eitohforge_sdk.core.config import AppSettings
from eitohforge_sdk.infrastructure.storage import CdnUrlRewriter, build_storage_public_url


def test_cdn_url_rewriter_rewrites_origin_urls() -> None:
    rewriter = CdnUrlRewriter(
        origin_base_url="https://origin.example/storage",
        cdn_base_url="https://cdn.example/assets",
    )
    assert (
        rewriter.build_cdn_url("tenant/file.png")
        == "https://cdn.example/assets/tenant/file.png"
    )


def test_build_storage_public_url_uses_configured_public_base_url() -> None:
    settings = AppSettings(
        storage={
            "provider": "local",
            "public_base_url": "https://files.example.com/public",
            "cdn_base_url": "https://cdn.example.com",
        }
    )
    assert (
        build_storage_public_url("tenant/avatar.jpg", settings.storage)
        == "https://cdn.example.com/tenant/avatar.jpg"
    )


def test_build_storage_public_url_for_s3_defaults_to_bucket_host() -> None:
    settings = AppSettings(
        storage={
            "provider": "s3",
            "bucket_name": "my-bucket",
            "region": "eu-west-1",
        }
    )
    assert (
        build_storage_public_url("public/a.txt", settings.storage)
        == "https://my-bucket.s3.eu-west-1.amazonaws.com/public/a.txt"
    )

