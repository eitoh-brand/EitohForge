"""Tests for platform-gap closures (flags, envelopes, registries, inbound HMAC)."""

from eitohforge_sdk.application.dto.envelope import err, ok, paginated
from eitohforge_sdk.core.abac import TenantMatchPolicy
from eitohforge_sdk.core.feature_flags import FeatureFlagDefinition, FeatureFlagService
from eitohforge_sdk.core.policy_registry import PolicyRegistry
from eitohforge_sdk.infrastructure.engine_registry import EngineRegistry
from eitohforge_sdk.infrastructure.webhooks.inbound import verify_body_hmac_hex


def test_feature_flag_mapping_roundtrip() -> None:
    d = FeatureFlagDefinition(
        key="k",
        enabled=True,
        rollout_percentage=42,
        actor_allowlist=("a",),
        tenant_allowlist=("t",),
    )
    m = d.to_mapping()
    d2 = FeatureFlagDefinition.from_mapping(m)
    assert d2.key == d.key
    assert d2.rollout_percentage == 42


def test_feature_flag_service_reload() -> None:
    svc = FeatureFlagService()
    svc.register(FeatureFlagDefinition(key="a", enabled=True))
    svc.reload([FeatureFlagDefinition(key="b", enabled=False)])
    assert "a" not in svc.flags
    assert svc.evaluate("b") is False


def test_envelope_helpers() -> None:
    r = ok(data={"x": 1})
    assert r.success is True
    assert r.data == {"x": 1}
    p = paginated(("a", "b"), total=2, page_size=10)
    assert len(p.data) == 2
    e = err(code="X", message="bad")
    assert e.success is False


def test_policy_registry() -> None:
    reg = PolicyRegistry()
    reg.register("tenant", TenantMatchPolicy())
    assert reg.get("tenant") is not None
    assert "tenant" in reg.names()


def test_engine_registry() -> None:
    reg = EngineRegistry()
    reg.register("primary", object())
    assert reg.get("primary") is not None


def test_verify_body_hmac_hex() -> None:
    body = b"hello"
    secret = "s"
    import hashlib
    import hmac

    sig = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    assert verify_body_hmac_hex(secret=secret, body=body, signature_hex=sig) is True
    assert verify_body_hmac_hex(secret=secret, body=body, signature_hex="00") is False
