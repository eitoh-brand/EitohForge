import pytest

from eitohforge_sdk.infrastructure.database import RepositoryBindingMap


def test_repository_binding_map_resolve() -> None:
    m = RepositoryBindingMap()
    m.bind("orders", "primary")
    m.bind("audit", "analytics")
    assert m.resolve("orders") == "primary"
    assert m.resolve_or("unknown", "primary") == "primary"
    assert m.names() == ("audit", "orders")


def test_repository_binding_map_resolve_missing() -> None:
    m = RepositoryBindingMap()
    with pytest.raises(KeyError):
        m.resolve("nope")


def test_repository_binding_rejects_empty() -> None:
    m = RepositoryBindingMap()
    with pytest.raises(ValueError):
        m.bind("", "primary")
