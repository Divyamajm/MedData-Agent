"""
MedData AI - In-Memory Query Caching & Invalidation Layer
==========================================================
Provides high-performance, deterministic LRU query caching for the expensive
Natural-Language-to-SQL translation and AST validation pipeline.

Architectural Design Decision (Why collections.OrderedDict over functools.lru_cache):
-----------------------------------------------------------------------------------
1. Granular Invalidation: `functools.lru_cache` does not support per-entry TTL
   expiry or targeted schema-drift eviction. `collections.OrderedDict` allows explicit
   timestamp checks per key and O(1) eviction via `popitem(last=False)`.
2. Schema-Aware Invalidation: Real-time hashing of `sqlite_master` detects DDL changes
   (tables/columns added or modified) and triggers an immediate global cache flush.
3. Healthcare Safety Bypasses: Urgent / acute emergency queries MUST NEVER be cached;
   a custom class allows declarative bypass hooks before cache insertion.
4. Introspection & Telemetry: Provides observable metrics (hits, misses, evictions,
   expirations, schema invalidations, hit ratio) for production monitoring and benchmarks.
5. Thread Safety: Uses `threading.Lock` to guarantee safe concurrent access in multi-threaded
   runtimes (FastAPI / Streamlit).
"""

import sys
import re
import time
import hashlib
import logging
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple, Union

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from models import (
    DomainType,
    IntentType,
    SearchFilters,
    HousingSearchFilters,
    CanonicalSpecialty,
    SortMetric,
    SortOrder,
)
from database import get_connection, DB_PATH
from safety import check_acute_emergency, validate_sql_sandbox_query

# ==============================================================================
# ⚙️ CONFIGURATION CONSTANTS
# ==============================================================================
DEFAULT_CACHE_MAX_SIZE: int = 100          # Maximum number of cached query plans
DEFAULT_CACHE_TTL_SECONDS: float = 600.0   # Time-to-Live in seconds (10 minutes)

logger = logging.getLogger("meddata_cache")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(message)s")


# ==============================================================================
# 🔤 QUERY NORMALIZATION
# ==============================================================================

def normalize_query(query: str) -> str:
    """
    Normalizes natural language prompts into a canonical cache key:
    - Lowercase conversion
    - Strips leading and trailing whitespace
    - Collapses multiple whitespace characters and newlines into a single space
    - Strips trailing punctuation (? . !) that doesn't change semantic intent
    """
    if not query:
        return ""
    q = query.strip().lower()
    # Strip trailing punctuation for canonicalization
    q = re.sub(r"[?!.,;]+$", "", q).strip()
    # Collapse all whitespace sequences into a single space
    q = re.sub(r"\s+", " ", q)
    return q


# ==============================================================================
# 🔍 SCHEMA HASHING (SCHEMA DRIFT DETECTION)
# ==============================================================================

def compute_schema_hash(db_path: str = DB_PATH) -> str:
    """
    Computes a deterministic SHA-256 hash of the SQLite database schema
    by querying sqlite_master for all non-system tables, views, and indexes.
    
    If any table/column is added, dropped, or altered, this hash changes,
    triggering an automatic invalidation of all cached query plans.
    """
    conn = None
    try:
        conn = get_connection(db_path)
        c = conn.cursor()
        c.execute("""
            SELECT type, name, tbl_name, sql 
            FROM sqlite_master 
            WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%'
            ORDER BY type, name
        """)
        rows = c.fetchall()
        schema_repr = "|".join(
            f"{row[0]}:{row[1]}:{row[2]}:{row[3].strip() if row[3] else ''}"
            for row in rows
        )
        return hashlib.sha256(schema_repr.encode("utf-8")).hexdigest()
    except Exception as e:
        logger.warning(f"[CACHE SCHEMA-ERROR] Unable to compute schema hash: {e}")
        return f"schema_error_{str(e)}"
    finally:
        if conn is not None:
            conn.close()


# ==============================================================================
# 📦 CACHED QUERY PLAN VALUE OBJECT
# ==============================================================================

@dataclass
class CachedQueryPlan:
    """
    Encapsulates the expensive output of the NL->SQL translation and AST validation step.
    Note: Only the validated SQL query and parameters are cached — NOT the raw database rows.
    """
    raw_query: str
    normalized_query: str
    sql_template: str
    params: List[Any]
    applied_filters: Dict[str, Any]
    domain: DomainType
    intent: IntentType
    filters: Optional[SearchFilters] = None
    housing_filters: Optional[HousingSearchFilters] = None
    explanation: str = ""
    timestamp: float = field(default_factory=time.time)
    schema_hash: str = ""
    is_ast_validated: bool = True
    compilation_time_ms: float = 0.0

    @property
    def age_seconds(self) -> float:
        return time.time() - self.timestamp

    def is_expired(self, ttl_seconds: float) -> bool:
        return self.age_seconds > ttl_seconds


# ==============================================================================
# 🧠 LRU QUERY CACHE WITH TTL & SCHEMA INVALIDATION
# ==============================================================================

class QueryCache:
    """
    Thread-safe, in-memory LRU cache with per-item TTL expiration and
    global schema-drift invalidation.
    """

    def __init__(
        self,
        max_size: int = DEFAULT_CACHE_MAX_SIZE,
        ttl_seconds: float = DEFAULT_CACHE_TTL_SECONDS,
        db_path: str = DB_PATH,
        schema_check_interval_seconds: float = 0.5
    ):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.db_path = db_path
        self.schema_check_interval_seconds = schema_check_interval_seconds
        self._cache: OrderedDict[str, CachedQueryPlan] = OrderedDict()
        self._lock = threading.Lock()
        self._current_schema_hash: str = compute_schema_hash(db_path)
        self._last_schema_check: float = time.time()

        # Telemetry & Observability counters
        self.stats = {
            "hits": 0,
            "misses": 0,
            "expirations": 0,
            "evictions": 0,
            "schema_invalidations": 0,
            "bypasses": 0,
            "puts": 0
        }

    def _check_and_handle_schema_change(self, force: bool = False) -> bool:
        """
        Detects if the database schema changed since the last check.
        If a drift is detected, flushes the entire cache and returns True.
        Throttled to schema_check_interval_seconds to avoid disk connection overhead on every get.
        Must be called while holding self._lock.
        """
        now = time.time()
        if not force and self.schema_check_interval_seconds > 0 and (now - self._last_schema_check) < self.schema_check_interval_seconds:
            return False

        self._last_schema_check = now
        fresh_hash = compute_schema_hash(self.db_path)
        if fresh_hash != self._current_schema_hash:
            prev_hash = self._current_schema_hash
            self._current_schema_hash = fresh_hash
            flushed_count = len(self._cache)
            self._cache.clear()
            self.stats["schema_invalidations"] += 1
            print(f"[CACHE SCHEMA-INVALIDATION] Schema drift detected! Flushed {flushed_count} cached entries. (Old: {prev_hash[:8]}... -> New: {fresh_hash[:8]}...)")
            logger.info(f"[CACHE SCHEMA-INVALIDATION] Schema drift detected! Flushed {flushed_count} cached entries.")
            return True
        return False

    def get(self, query: str, force_schema_check: bool = False) -> Optional[CachedQueryPlan]:
        """
        Retrieves a cached query plan if present, non-expired, and schema-valid.
        Returns None on miss, expiry, or schema invalidation.
        """
        norm_key = normalize_query(query)
        if not norm_key:
            return None

        with self._lock:
            # 1. Check for schema change (throttled check or forced)
            self._check_and_handle_schema_change(force=force_schema_check)

            # 2. Lookup normalized key in LRU store
            if norm_key not in self._cache:
                self.stats["misses"] += 1
                logger.debug(f"[CACHE MISS] Key: '{norm_key}'")
                return None

            entry = self._cache[norm_key]

            # 3. Check TTL expiration
            if entry.is_expired(self.ttl_seconds):
                del self._cache[norm_key]
                self.stats["expirations"] += 1
                self.stats["misses"] += 1
                print(f"[CACHE EXPIRY] Entry for '{norm_key}' expired (age: {entry.age_seconds:.1f}s > TTL: {self.ttl_seconds}s). Evicting.")
                logger.info(f"[CACHE EXPIRY] Entry for '{norm_key}' expired (age: {entry.age_seconds:.1f}s > TTL: {self.ttl_seconds}s).")
                return None

            # 4. Check schema hash match on the individual item
            if entry.schema_hash and entry.schema_hash != self._current_schema_hash:
                del self._cache[norm_key]
                self.stats["schema_invalidations"] += 1
                self.stats["misses"] += 1
                print(f"[CACHE SCHEMA-INVALIDATION] Entry '{norm_key}' schema hash mismatch. Evicting.")
                return None

            # 5. Cache HIT: Move to most-recently-used position
            self._cache.move_to_end(norm_key)
            self.stats["hits"] += 1
            logger.info(f"[CACHE HIT] Key: '{norm_key}' (age: {entry.age_seconds:.2f}s)")
            return entry

    def put(self, query: str, plan: CachedQueryPlan) -> bool:
        """
        Inserts or updates a validated query plan in the cache.
        Enforces LRU capacity eviction and bypasses urgent healthcare queries.
        Returns True if cached, False if bypassed or invalid.
        """
        # CRITICAL SAFETY INVARIANT:
        # Urgent / emergency healthcare queries must NEVER be cached to prevent
        # serving stale protocols during life-threatening medical emergencies.
        if plan.intent == IntentType.EMERGENCY or check_acute_emergency(query) is not None:
            with self._lock:
                self.stats["bypasses"] += 1
            print(f"[CACHE BYPASS] Urgent/Emergency healthcare query bypassed caching for patient safety.")
            logger.info("[CACHE BYPASS] Urgent/Emergency healthcare query bypassed caching.")
            return False

        norm_key = normalize_query(query)
        if not norm_key:
            return False

        with self._lock:
            # Refresh schema hash tag on entry
            plan.schema_hash = self._current_schema_hash
            plan.normalized_query = norm_key
            plan.timestamp = time.time()

            # If key already exists, update and move to MRU
            if norm_key in self._cache:
                self._cache[norm_key] = plan
                self._cache.move_to_end(norm_key)
                self.stats["puts"] += 1
                print(f"[CACHE UPDATE] Updated plan for '{norm_key}'")
                return True

            # If cache is at max capacity, evict the least recently used (first item)
            if len(self._cache) >= self.max_size:
                evicted_key, _ = self._cache.popitem(last=False)
                self.stats["evictions"] += 1
                print(f"[CACHE EVICT] LRU capacity reached ({self.max_size}). Evicted oldest entry: '{evicted_key}'")
                logger.info(f"[CACHE EVICT] Evicted oldest entry: '{evicted_key}'")

            self._cache[norm_key] = plan
            self._cache.move_to_end(norm_key)
            self.stats["puts"] += 1
            print(f"[CACHE PUT] Cached validated SQL plan for '{norm_key}' (total: {len(self._cache)}/{self.max_size})")
            logger.info(f"[CACHE PUT] Cached plan for '{norm_key}'")
            return True

    def invalidate_all(self) -> int:
        """Flushes all entries from the cache."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._current_schema_hash = compute_schema_hash(self.db_path)
            print(f"[CACHE FLUSH] Cleared all {count} cached entries.")
            return count

    def invalidate_key(self, query: str) -> bool:
        """Removes a specific normalized query from the cache."""
        norm_key = normalize_query(query)
        with self._lock:
            if norm_key in self._cache:
                del self._cache[norm_key]
                print(f"[CACHE INVALIDATE] Removed key: '{norm_key}'")
                return True
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Returns diagnostic metrics and telemetry."""
        with self._lock:
            total_lookups = self.stats["hits"] + self.stats["misses"]
            hit_ratio = round((self.stats["hits"] / total_lookups * 100.0), 2) if total_lookups > 0 else 0.0
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "ttl_seconds": self.ttl_seconds,
                "hits": self.stats["hits"],
                "misses": self.stats["misses"],
                "expirations": self.stats["expirations"],
                "evictions": self.stats["evictions"],
                "schema_invalidations": self.stats["schema_invalidations"],
                "bypasses": self.stats["bypasses"],
                "puts": self.stats["puts"],
                "hit_ratio_percent": hit_ratio,
                "current_schema_hash": self._current_schema_hash[:12] + "..." if self._current_schema_hash else "None"
            }


# Global singleton instance for use across the application
global_query_cache = QueryCache()


# ==============================================================================
# 🚀 CACHED QUERY PIPELINE COMPILER
# ==============================================================================

def compile_and_validate_query_with_cache(
    prompt: str,
    engine: str = "deterministic",
    api_key: Optional[str] = None,
    provider: str = "gemini",
    db_path: str = DB_PATH,
    use_cache: bool = True,
    cache_instance: Optional[QueryCache] = None
) -> Tuple[CachedQueryPlan, bool, float]:
    """
    Executes the end-to-end NL->SQL Translation + AST Validation pipeline with query caching.
    
    Steps:
    1. Check Cache: If enabled, attempts LRU cache lookup.
       - If HIT: Returns cached plan immediately (sub-millisecond latency).
    2. Intent & Safety Parsing: Dual-Engine parsing (Deterministic regex or Bounded LLM).
    3. Safety Guardrails: Emergency checks, medical advice refusal, injection defense.
    4. Deterministic Parameterized SQL Generation: Builds safe SQL query template and parameters.
    5. AST Validation: Verifies SQL syntax and security rules via sqlglot AST parser.
    6. Cache Insertion: If query is safe and not an emergency, stores in LRU cache.
    
    Returns:
        (CachedQueryPlan, is_cache_hit: bool, latency_ms: float)
    """
    cache = cache_instance or global_query_cache
    start_time = time.perf_counter()

    # 1. Cache Lookup (if enabled)
    if use_cache:
        cached_plan = cache.get(prompt)
        if cached_plan is not None:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 3)
            return cached_plan, True, latency_ms

    # 2. Cache Miss: Execute expensive translation + validation pipeline
    from intent_parser import parse_user_intent_hybrid
    from query_engine import build_safe_query, build_safe_housing_query

    classification, engine_used, parse_lat = parse_user_intent_hybrid(
        prompt,
        engine=engine,
        api_key=api_key,
        provider=provider
    )

    # 3. Parameterized SQL Generation & AST Validation
    sql_template = ""
    params: List[Any] = []
    applied_filters: Dict[str, Any] = {}

    if classification.domain == DomainType.REAL_ESTATE and classification.housing_filters:
        sql_template, params, applied_filters = build_safe_housing_query(classification.housing_filters)
    else:
        filters = classification.filters or SearchFilters()
        sql_template, params, applied_filters = build_safe_query(filters)

    # 4. AST Syntactic and Table Allowlist Verification
    is_ast_safe = True
    if sql_template:
        is_ast_safe, _ = validate_sql_sandbox_query(sql_template)

    compilation_lat_ms = round((time.perf_counter() - start_time) * 1000, 3)

    plan = CachedQueryPlan(
        raw_query=prompt,
        normalized_query=normalize_query(prompt),
        sql_template=sql_template,
        params=params,
        applied_filters=applied_filters,
        domain=classification.domain,
        intent=classification.intent,
        filters=classification.filters,
        housing_filters=classification.housing_filters,
        explanation=classification.explanation,
        timestamp=time.time(),
        schema_hash=cache._current_schema_hash,
        is_ast_validated=is_ast_safe,
        compilation_time_ms=compilation_lat_ms
    )

    # 5. Insert into Cache (Only if cache is enabled and query is not an acute emergency)
    if use_cache:
        cache.put(prompt, plan)

    total_lat_ms = round((time.perf_counter() - start_time) * 1000, 3)
    return plan, False, total_lat_ms
