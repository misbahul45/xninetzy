from __future__ import annotations

import time


def test_cache_miss_returns_none_and_increments_misses():
    from xninetzy.os.career.search_cache import SearchCache

    cache = SearchCache()
    assert cache.get("k") is None
    assert cache.stats()["misses"] == 1


def test_cache_put_then_get_returns_value():
    from xninetzy.os.career.search_cache import SearchCache

    cache = SearchCache()
    cache.put(key="k1", adapter_id="remoteok", value=[{"id": 1}])
    assert cache.get("k1") == [{"id": 1}]
    stats = cache.stats()
    assert stats["hits"] == 1
    assert stats["stores"] == 1


def test_cache_expires_after_ttl():
    from xninetzy.os.career.search_cache import SearchCache

    cache = SearchCache(ttl_overrides={"remoteok": 1})
    cache.put(key="k1", adapter_id="remoteok", value=[{"id": 1}])
    assert cache.get("k1") == [{"id": 1}]
    time.sleep(1.2)
    assert cache.get("k1") is None
    assert cache.stats()["evictions"] >= 1


def test_cache_ttl_differs_per_adapter():
    from xninetzy.os.career.search_cache import SearchCache

    cache = SearchCache()
    assert cache.ttl_for("remoteok") == 1800
    assert cache.ttl_for("kalibrr") == 300
    assert cache.ttl_for("jobstreet_id") == 60
    assert cache.ttl_for("unknown_adapter") >= 60


def test_cache_key_stable_across_calls():
    from xninetzy.os.career.search_cache import SearchCache

    cache = SearchCache()
    k1 = cache.make_key(adapter_id="remoteok", query="Backend Engineer", country="", work_mode="any")
    k2 = cache.make_key(adapter_id="remoteok", query="  backend engineer  ", country="", work_mode="any")
    assert k1 == k2


def test_cache_keys_differ_across_dimensions():
    from xninetzy.os.career.search_cache import SearchCache

    cache = SearchCache()
    base = cache.make_key(adapter_id="remoteok", query="x", country="", work_mode="any")
    other_adapter = cache.make_key(adapter_id="arbeitnow", query="x", country="", work_mode="any")
    other_query = cache.make_key(adapter_id="remoteok", query="y", country="", work_mode="any")
    other_country = cache.make_key(adapter_id="remoteok", query="x", country="ID", work_mode="any")
    assert base != other_adapter
    assert base != other_query
    assert base != other_country


def test_cache_clear_for_one_adapter_keeps_others():
    from xninetzy.os.career.search_cache import SearchCache

    cache = SearchCache()
    cache.put(key="a", adapter_id="remoteok", value=1)
    cache.put(key="b", adapter_id="arbeitnow", value=2)
    removed = cache.clear("remoteok")
    assert removed == 1
    assert cache.get("a") is None
    assert cache.get("b") == 2


def test_cache_evicts_oldest_when_full():
    from xninetzy.os.career.search_cache import SearchCache

    cache = SearchCache(max_entries=2)
    cache.put(key="a", adapter_id="remoteok", value=1)
    cache.put(key="b", adapter_id="remoteok", value=2)
    cache.put(key="c", adapter_id="remoteok", value=3)
    assert cache.get("a") is None
    assert cache.get("c") == 3


def test_cache_stats_report_per_adapter_counts():
    from xninetzy.os.career.search_cache import SearchCache

    cache = SearchCache()
    cache.put(key="a", adapter_id="remoteok", value=1)
    cache.put(key="b", adapter_id="kalibrr", value=2)
    cache.put(key="c", adapter_id="remoteok", value=3)
    stats = cache.stats()
    assert stats["by_adapter"]["remoteok"]["count"] == 2
    assert stats["by_adapter"]["kalibrr"]["count"] == 1
