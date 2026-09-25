"""
MedData AI - Query Caching Performance Benchmark
=================================================
Measures empirical throughput, latency reduction, and hit rates for the
NL->SQL Translation and AST Validation pipeline with LRU Caching enabled vs disabled.

Usage:
    python benchmark.py
    python benchmark.py --iterations 3
"""

import sys
import time
import argparse
from typing import List, Dict, Any, Tuple, Optional

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from query_cache import (
    QueryCache,
    compile_and_validate_query_with_cache,
    DEFAULT_CACHE_MAX_SIZE,
    DEFAULT_CACHE_TTL_SECONDS
)
from database import init_database, DB_PATH

# 18 Representative Clinical Healthcare Queries (10 Unique + 8 Repeated/Normalized Variants)
BENCHMARK_QUERIES: List[Tuple[str, bool]] = [
    # (Query Text, Is_Expected_Repeat)
    ("Find a cardiologist in Chennai under ₹1500 available today", False),
    ("Show me heart doctors nearby", False),
    ("Cardiac surgeon at Apollo Hospital Chennai", False),
    ("I need a neurologist in Bangalore", False),
    ("Orthopedic surgeon for knee replacement", False),
    ("Find a cardiologist in Chennai under ₹1500 available today", True),   # Repeat of 1 (Exact)
    ("Pediatrician for infant vaccination", False),
    ("Neurologist with satisfaction above 90 under ₹2000", False),
    ("   find a cardiologist in chennai under ₹1500 available today?  ", True), # Repeat of 1 (Whitespace/Punctuation normalized)
    ("Show me all doctors", False),
    ("Show me heart doctors nearby", True),                                 # Repeat of 2 (Exact)
    ("Find Dr. Rajesh Sharma", False),
    ("Cardiac surgeon at Apollo Hospital Chennai", True),                  # Repeat of 3 (Exact)
    ("Cheapest doctor available today", False),
    ("i need a neurologist in bangalore", True),                            # Repeat of 4 (Case variation)
    ("Pediatrician under ₹1000 available today", False),
    ("Orthopedic surgeon for knee replacement", True),                      # Repeat of 5 (Exact)
    ("Show me all doctors", True),                                         # Repeat of 10 (Exact)
]


def run_benchmark_pass(
    queries: List[Tuple[str, bool]],
    use_cache: bool,
    cache_instance: Optional[QueryCache] = None
) -> Dict[str, Any]:
    """
    Executes a single pass over the benchmark query set either with or without caching.
    Measures individual query latencies and partitions repeated vs unique queries.
    """
    latencies_all = []
    latencies_unique = []
    latencies_repeats = []
    hits = 0
    misses = 0

    for query_text, is_repeat in queries:
        start = time.perf_counter()
        plan, is_hit, compile_ms = compile_and_validate_query_with_cache(
            prompt=query_text,
            engine="deterministic",
            use_cache=use_cache,
            cache_instance=cache_instance
        )
        duration_ms = (time.perf_counter() - start) * 1000.0

        latencies_all.append(duration_ms)
        if is_repeat:
            latencies_repeats.append(duration_ms)
        else:
            latencies_unique.append(duration_ms)

        if is_hit:
            hits += 1
        else:
            misses += 1

    total_time_ms = sum(latencies_all)
    avg_all_ms = total_time_ms / len(latencies_all) if latencies_all else 0.0
    avg_unique_ms = sum(latencies_unique) / len(latencies_unique) if latencies_unique else 0.0
    avg_repeat_ms = sum(latencies_repeats) / len(latencies_repeats) if latencies_repeats else 0.0

    return {
        "use_cache": use_cache,
        "total_queries": len(queries),
        "total_time_ms": total_time_ms,
        "avg_latency_ms": avg_all_ms,
        "avg_unique_ms": avg_unique_ms,
        "avg_repeat_ms": avg_repeat_ms,
        "hits": hits,
        "misses": misses,
        "hit_rate_pct": (hits / len(queries) * 100.0) if queries else 0.0,
        "latencies": latencies_all
    }


def run_benchmark(iterations: int = 1) -> Dict[str, Any]:
    """
    Runs full benchmark comparing caching disabled vs enabled over specified iterations.
    """
    init_database(force_reset=False)

    print("=" * 72)
    print("MEDDATA AI -- QUERY CACHING & INVALIDATION BENCHMARK")
    print("=" * 72)
    print(f"Total Queries in Test Set: {len(BENCHMARK_QUERIES)} (10 Unique, 8 Repeated/Normalized)")
    print(f"Cache Configuration: Max Size = {DEFAULT_CACHE_MAX_SIZE}, TTL = {DEFAULT_CACHE_TTL_SECONDS}s")
    print(f"Iterations: {iterations}")
    print("-" * 72)

    # 1. Warm up & Run WITHOUT Caching
    uncached_results = []
    for _ in range(iterations):
        uncached_results.append(run_benchmark_pass(BENCHMARK_QUERIES, use_cache=False))

    # 2. Run WITH Caching (Fresh Cache Instance)
    cached_results = []
    test_cache = QueryCache(max_size=DEFAULT_CACHE_MAX_SIZE, ttl_seconds=DEFAULT_CACHE_TTL_SECONDS)
    for _ in range(iterations):
        cached_results.append(run_benchmark_pass(BENCHMARK_QUERIES, use_cache=True, cache_instance=test_cache))

    # Average metrics over iterations
    uncached_total_time = sum(r["total_time_ms"] for r in uncached_results) / iterations
    uncached_avg_lat = sum(r["avg_latency_ms"] for r in uncached_results) / iterations
    uncached_repeat_lat = sum(r["avg_repeat_ms"] for r in uncached_results) / iterations

    cached_total_time = sum(r["total_time_ms"] for r in cached_results) / iterations
    cached_avg_lat = sum(r["avg_latency_ms"] for r in cached_results) / iterations
    cached_repeat_lat = sum(r["avg_repeat_ms"] for r in cached_results) / iterations

    # Latency and Time Reduction calculations
    total_time_reduction_pct = ((uncached_total_time - cached_total_time) / uncached_total_time) * 100.0 if uncached_total_time > 0 else 0.0
    repeat_latency_reduction_pct = ((uncached_repeat_lat - cached_repeat_lat) / uncached_repeat_lat) * 100.0 if uncached_repeat_lat > 0 else 0.0

    num_repeats = len([q for q, is_rep in BENCHMARK_QUERIES if is_rep])
    cold_pass_hits = cached_results[0]["hits"]
    repeat_hit_rate = (cold_pass_hits / num_repeats * 100.0) if num_repeats > 0 else 0.0
    hit_str = f"{cold_pass_hits}/{num_repeats} ({repeat_hit_rate:.1f}%)"

    print(f"{'Metric':<38} | {'No Cache':<14} | {'With Cache':<14}")
    print("-" * 72)
    print(f"{'Total Pipeline Time (18 Queries)':<38} | {uncached_total_time:>10.3f} ms | {cached_total_time:>10.3f} ms")
    print(f"{'Average Latency per Query':<38} | {uncached_avg_lat:>10.3f} ms | {cached_avg_lat:>10.3f} ms")
    print(f"{'Average Latency on Repeated Queries':<38} | {uncached_repeat_lat:>10.3f} ms | {cached_repeat_lat:>10.3f} ms")
    print(f"{'Cache Hits on Repeated Queries':<38} | {f'0/{num_repeats} (0.0%)':<14} | {hit_str:<14}")
    print("-" * 72)
    print(f"Overall Total Time Reduction: {total_time_reduction_pct:.1f}%")
    print(f"Latency Reduction on Repeated Queries: {repeat_latency_reduction_pct:.1f}%")
    print("=" * 72)

    return {
        "uncached_total_time_ms": uncached_total_time,
        "cached_total_time_ms": cached_total_time,
        "uncached_avg_lat_ms": uncached_avg_lat,
        "cached_avg_lat_ms": cached_avg_lat,
        "uncached_repeat_lat_ms": uncached_repeat_lat,
        "cached_repeat_lat_ms": cached_repeat_lat,
        "total_time_reduction_pct": total_time_reduction_pct,
        "repeat_latency_reduction_pct": repeat_latency_reduction_pct,
        "cache_stats": test_cache.get_stats()
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MedData AI Query Caching Benchmark")
    parser.add_argument("--iterations", type=int, default=1, help="Number of benchmark iterations (default: 1)")
    args = parser.parse_args()
    run_benchmark(iterations=args.iterations)
