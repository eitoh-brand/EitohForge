from eitohforge_sdk.infrastructure.cache import AdvancedCacheProvider, MemoryCacheProvider


def test_invalidate_by_tag() -> None:
    cache = AdvancedCacheProvider(delegate=MemoryCacheProvider())
    cache.set_with_tags("users:1", {"name": "u1"}, tags=("users",))
    cache.set_with_tags("users:2", {"name": "u2"}, tags=("users",))
    cache.set_with_tags("orders:1", {"id": "o1"}, tags=("orders",))

    removed = cache.invalidate_tag("users")
    assert removed == 2
    assert cache.get("users:1") is None
    assert cache.get("users:2") is None
    assert cache.get("orders:1") == {"id": "o1"}


def test_invalidate_by_prefix() -> None:
    cache = AdvancedCacheProvider(delegate=MemoryCacheProvider())
    cache.set("tenant-a:users:1", {"id": "u1"})
    cache.set("tenant-a:users:2", {"id": "u2"})
    cache.set("tenant-b:users:1", {"id": "u3"})

    removed = cache.invalidate_prefix("tenant-a:")
    assert removed == 2
    assert cache.get("tenant-a:users:1") is None
    assert cache.get("tenant-a:users:2") is None
    assert cache.get("tenant-b:users:1") == {"id": "u3"}


def test_write_through_updates_cache_and_invalidates_related_prefixes() -> None:
    cache = AdvancedCacheProvider(delegate=MemoryCacheProvider())
    cache.set("users:list:tenant-a", [{"id": "old"}])
    cache.write_through(
        "users:1",
        {"id": "users:1", "name": "new"},
        tags=("users",),
        invalidate_prefixes=("users:list:",),
    )

    assert cache.get("users:list:tenant-a") is None
    assert cache.get("users:1") == {"id": "users:1", "name": "new"}

