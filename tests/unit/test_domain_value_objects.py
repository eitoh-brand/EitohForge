from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from eitohforge_sdk.domain.value_objects import (
    CorrelationId,
    DateTimeRange,
    DomainInvariantError,
    EmailAddress,
    EntityId,
    TenantId,
)


def test_email_address_normalizes_and_validates() -> None:
    email = EmailAddress("  USER@Example.Com ")
    assert email.value == "user@example.com"


def test_email_address_rejects_invalid_input() -> None:
    with pytest.raises(DomainInvariantError):
        EmailAddress("invalid-email")


def test_tenant_id_and_entity_id_validation() -> None:
    assert TenantId("tenant_alpha-1").value == "tenant_alpha-1"
    assert EntityId("user:abc_123").value == "user:abc_123"
    with pytest.raises(DomainInvariantError):
        TenantId("Tenant-Upper")


def test_correlation_id_requires_uuid() -> None:
    value = "1d21c4fd-4349-42a3-b272-6a4a2bd611fd"
    assert CorrelationId(value).value == value
    with pytest.raises(DomainInvariantError):
        CorrelationId("not-a-uuid")


def test_datetime_range_invariant() -> None:
    start = datetime.now(UTC)
    end = start + timedelta(minutes=5)
    assert DateTimeRange(start=start, end=end).start == start
    with pytest.raises(DomainInvariantError):
        DateTimeRange(start=end, end=start)

