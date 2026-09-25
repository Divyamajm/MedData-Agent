"""
Unit Tests for In-Memory Query Caching & Invalidation Layer
===========================================================
Tests LRU eviction, TTL expiration, schema-drift invalidation,
urgent healthcare query bypass, and normalization.
"""

import time
import sqlite3
import pytest
from unittest.mock import patch

from query_cache import (
    QueryCache,
    CachedQueryPlan,
    normalize_query,
    compute_schema_hash,
    compile_and_validate_query_with_cache
)
from models import (
    DomainType,
    IntentType,
    SearchFilters,
    CanonicalSpecialty
)
from database import get_connection, DB_PATH, init_database


@pytest.fixture
def clean_db():
    """Ensures database is initialized before tests."""
    init_database(force_reset=False)


@pytest.fixture
def sample_plan():
    """Creates a sample CachedQueryPlan object."""
    return CachedQueryPlan(
        raw_query="Find a cardiologist in Chennai under ₹1500",
        normalized_query="find a cardiologist in chennai under ₹1500",
        sql_template="SELECT * FROM Doctors WHERE specialty = ? AND consultation_fee <= ?;",
        params=["Cardiology", 1500],
        applied_filters={"specialty": "Cardiology", "max_fee": 1500},
        domain=DomainType.HEALTHCARE,
        intent=IntentType.DOCTOR_SEARCH,
        filters=SearchFilters(specialty=CanonicalSpecialty.CARDIOLOGY, max_fee=1500),
        timestamp=time.time(),
        schema_hash="dummy_hash_123",
        is_ast_validated=True
    )


# ==============================================================================
# 1. NORMALIZATION TESTS
# ==============================================================================

def test_query_normalization_whitespace_and_casing():
    """Verifies that query normalization collapses whitespace, lowers case, and strips punctuation."""
    q1 = "Find a Cardiologist"
    q2 = "   find   a   cardiologist   "
    q3 = "FIND A CARDIOLOGIST?"
    q4 = "find a cardiologist!"

    assert normalize_query(q1) == "find a cardiologist"
    assert normalize_query(q2) == "find a cardiologist"
    assert normalize_query(q3) == "find a cardiologist"
    assert normalize_query(q4) == "find a cardiologist"
    assert normalize_query(q1) == normalize_query(q2) == normalize_query(q3) == normalize_query(q4)


# ==============================================================================
# 2. CACHE HIT & PIPELINE CALL COUNT TESTS
# ==============================================================================

def test_cache_hit_returns_same_sql_without_recompilation(clean_db, sample_plan):
    """
    Verifies that a cache hit returns the cached SQL template and parameters
    without re-invoking intent parsing or SQL generation.
    """
    cache = QueryCache(max_size=10, ttl_seconds=60)
    query = "Find a cardiologist in Chennai under ₹1500"

    # Put sample plan in cache
    cache.put(query, sample_plan)

    # First lookup: Cache HIT
    hit_plan = cache.get(query)
    assert hit_plan is not None
    assert hit_plan.sql_template == sample_plan.sql_template
    assert hit_plan.params == sample_plan.params
    assert cache.stats["hits"] == 1
    assert cache.stats["misses"] == 0

    # Look up normalized variant: Cache HIT
    variant_query = "   FIND a Cardiologist in Chennai under ₹1500?  "
    hit_variant = cache.get(variant_query)
    assert hit_variant is not None
    assert hit_variant.sql_template == sample_plan.sql_template
    assert cache.stats["hits"] == 2


def test_compile_pipeline_skips_parsing_on_cache_hit(clean_db):
    """
    Mocks parse_user_intent_hybrid and confirms that it is invoked exactly once
    on initial query, and 0 times on subsequent repeated queries.
    """
    cache = QueryCache(max_size=10, ttl_seconds=60)
    query = "Find a cardiologist in Chennai"

    with patch("intent_parser.parse_user_intent_hybrid", wraps=__import__("intent_parser").parse_user_intent_hybrid) as mock_parser:
        # First call: Cache MISS -> Parser invoked once
        plan1, is_hit1, lat1 = compile_and_validate_query_with_cache(query, use_cache=True, cache_instance=cache)
        assert is_hit1 is False
        assert mock_parser.call_count == 1

        # Second call (exact query): Cache HIT -> Parser NOT invoked
        plan2, is_hit2, lat2 = compile_and_validate_query_with_cache(query, use_cache=True, cache_instance=cache)
        assert is_hit2 is True
        assert mock_parser.call_count == 1  # Call count unchanged!
        assert plan2.sql_template == plan1.sql_template

        # Third call (whitespace variation): Cache HIT -> Parser NOT invoked
        plan3, is_hit3, lat3 = compile_and_validate_query_with_cache("  FIND A CARDIOLOGIST IN CHENNAI?  ", use_cache=True, cache_instance=cache)
        assert is_hit3 is True
        assert mock_parser.call_count == 1  # Still 1!


# ==============================================================================
# 3. TTL EXPIRATION TESTS
# ==============================================================================

def test_cache_ttl_expiry_forces_regeneration(clean_db, sample_plan):
    """
    Verifies that when an entry exceeds its TTL, cache.get() treats it as a MISS,
    evicts the stale entry, increments expiration stats, and triggers regeneration.
    """
    # Create cache with very short TTL (0.1 seconds)
    short_ttl_cache = QueryCache(max_size=10, ttl_seconds=0.1)
    query = "Find a cardiologist in Chennai under ₹1500"

    short_ttl_cache.put(query, sample_plan)
    assert short_ttl_cache.get(query) is not None
    assert short_ttl_cache.stats["hits"] == 1

    # Sleep past the TTL
    time.sleep(0.15)

    # Second lookup: should be EXPIRED
    expired_result = short_ttl_cache.get(query)
    assert expired_result is None
    assert short_ttl_cache.stats["expirations"] == 1
    assert short_ttl_cache.stats["misses"] == 1
    assert len(short_ttl_cache._cache) == 0


# ==============================================================================
# 4. SCHEMA DRIFT / SCHEMA CHANGE INVALIDATION TESTS
# ==============================================================================

def test_schema_change_flushes_cache(clean_db, sample_plan):
    """
    Verifies that modifying the database schema (e.g. creating/dropping a temporary table)
    changes the schema hash and automatically flushes the cache on the next access.
    """
    # Ensure temporary table does not exist prior to test
    conn = get_connection(DB_PATH)
    try:
        conn.execute("DROP TABLE IF EXISTS _test_schema_migration_temp;")
        conn.commit()
    finally:
        conn.close()

    cache = QueryCache(max_size=10, ttl_seconds=600, schema_check_interval_seconds=0.0)
    query = "Find a cardiologist in Chennai"

    # Populate cache
    cache.put(query, sample_plan)
    assert len(cache._cache) == 1
    assert cache.get(query) is not None

    # Simulate a schema change (DDL: CREATE TABLE)
    conn = get_connection(DB_PATH)
    try:
        conn.execute("CREATE TABLE _test_schema_migration_temp (id INTEGER PRIMARY KEY, flag TEXT);")
        conn.commit()
    finally:
        conn.close()

    # Next cache access should detect schema drift and flush all entries
    flushed_lookup = cache.get(query)
    assert flushed_lookup is None
    assert cache.stats["schema_invalidations"] == 1
    assert len(cache._cache) == 0

    # Cleanup temporary table
    conn = get_connection(DB_PATH)
    try:
        conn.execute("DROP TABLE IF EXISTS _test_schema_migration_temp;")
        conn.commit()
    finally:
        conn.close()


# ==============================================================================
# 5. URGENT / EMERGENCY TRIAGE BYPASS TESTS
# ==============================================================================

def test_emergency_queries_are_never_cached(clean_db):
    """
    CRITICAL SAFETY TEST:
    Verifies that life-threatening acute emergency queries (chest pain, can't breathe, etc.)
    bypass the cache completely and are NEVER stored.
    """
    cache = QueryCache(max_size=10, ttl_seconds=600)
    emergency_query = "I am having severe chest pain and struggling to breathe"

    # 1. Compile through pipeline
    plan, is_hit, lat = compile_and_validate_query_with_cache(
        emergency_query,
        use_cache=True,
        cache_instance=cache
    )
    assert plan.intent == IntentType.EMERGENCY
    assert is_hit is False

    # 2. Check that it was NOT stored in the cache
    assert len(cache._cache) == 0
    assert cache.stats["bypasses"] == 1
    assert cache.get(emergency_query) is None

    # 3. Direct put() attempt should also be rejected
    put_result = cache.put(emergency_query, plan)
    assert put_result is False
    assert len(cache._cache) == 0


# ==============================================================================
# 6. LRU CAPACITY EVICTION TESTS
# ==============================================================================

def test_lru_capacity_eviction():
    """
    Verifies that when cache reaches max_size, the Least Recently Used item is evicted.
    """
    cache = QueryCache(max_size=3, ttl_seconds=600)

    def make_plan(q: str):
        return CachedQueryPlan(
            raw_query=q,
            normalized_query=normalize_query(q),
            sql_template=f"SELECT * FROM Doctors WHERE name = '{q}';",
            params=[],
            applied_filters={},
            domain=DomainType.HEALTHCARE,
            intent=IntentType.DOCTOR_SEARCH,
            timestamp=time.time()
        )

    # Insert 3 items (at max capacity)
    cache.put("Query A", make_plan("Query A"))
    cache.put("Query B", make_plan("Query B"))
    cache.put("Query C", make_plan("Query C"))
    assert len(cache._cache) == 3

    # Access Query A (making Query B the LRU item)
    cache.get("Query A")

    # Insert 4th item -> Query B should be evicted
    cache.put("Query D", make_plan("Query D"))
    assert len(cache._cache) == 3
    assert cache.stats["evictions"] == 1

    # Query B should be gone
    assert cache.get("Query B") is None
    # Query A, C, D should still be present
    assert cache.get("Query A") is not None
    assert cache.get("Query C") is not None
    assert cache.get("Query D") is not None


# ==============================================================================
# 7. CACHE TELEMETRY & STATS
# ==============================================================================

def test_cache_telemetry_stats():
    """Verifies that stats dictionary accurately reflects hits, misses, and hit ratio."""
    cache = QueryCache(max_size=5, ttl_seconds=600)
    stats0 = cache.get_stats()
    assert stats0["size"] == 0
    assert stats0["hit_ratio_percent"] == 0.0

    plan = CachedQueryPlan(
        raw_query="Test query",
        normalized_query="test query",
        sql_template="SELECT 1;",
        params=[],
        applied_filters={},
        domain=DomainType.HEALTHCARE,
        intent=IntentType.DOCTOR_SEARCH,
        timestamp=time.time()
    )
    cache.put("Test query", plan)
    cache.get("Test query")   # Hit 1
    cache.get("Test query")   # Hit 2
    cache.get("Unknown query") # Miss 1

    stats = cache.get_stats()
    assert stats["hits"] == 2
    assert stats["misses"] == 1
    assert stats["size"] == 1
    assert stats["hit_ratio_percent"] == 66.67
