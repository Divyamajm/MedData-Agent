"""
MedData AI -- In-Process ASGI Concurrency Dispatch Benchmark Suite
===================================================================
Simulates concurrent multi-threaded client traffic against the MedData FastAPI service layer.
NOTE: This measures in-process in-memory ASGI dispatch throughput (function call overhead
and DB query performance), not socket-level network stack I/O.

Measures throughput (RPS), error rates, and p50/p95/p99 latency percentiles across
concurrency levels (10, 50, 100 concurrent workers).

Run via:
    python -m tests.load_test
"""

import os
import time
import statistics
import concurrent.futures
from typing import List, Dict, Any
from fastapi.testclient import TestClient

# Ensure demo auth is enabled for local load testing if unconfigured
os.environ.setdefault("MEDDATA_ALLOW_UNAUTHENTICATED_DEMO", "true")

from api import app


def execute_triage_request(client: TestClient, query: str, client_ip: str = "127.0.0.1") -> Dict[str, Any]:
    """Sends a single triage POST request and records response time."""
    start = time.perf_counter()
    headers = {"X-Forwarded-For": client_ip}
    api_key = os.getenv("MEDDATA_API_KEY")
    if api_key:
        headers["X-API-Key"] = api_key

    try:
        response = client.post(
            "/api/v1/triage/query",
            json={"query": query, "engine": "deterministic"},
            headers=headers
        )
        latency_ms = (time.perf_counter() - start) * 1000
        return {
            "status_code": response.status_code,
            "latency_ms": latency_ms,
            "success": response.status_code == 200
        }
    except Exception as e:
        latency_ms = (time.perf_counter() - start) * 1000
        return {
            "status_code": 500,
            "latency_ms": latency_ms,
            "success": False,
            "error": str(e)
        }


def run_concurrency_tier(concurrency_level: int, total_requests: int) -> Dict[str, Any]:
    """Executes a batch of requests across N concurrent worker threads."""
    import logging
    logging.getLogger("meddata_api").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    test_queries = [
        "Find a cardiologist in Chennai under 1500",
        "Who is the nearest neurologist?",
        "Find a 3BHK flat in Koramangala under 60000",
        "Find doctors available today in Mumbai",
        "What is the cheapest pediatrician in Delhi?"
    ]

    client = TestClient(app)
    results: List[Dict[str, Any]] = []

    overall_start = time.perf_counter()

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency_level) as executor:
        futures = [
            executor.submit(
                execute_triage_request, 
                client, 
                test_queries[i % len(test_queries)],
                f"10.0.{i % concurrency_level}.{(i // concurrency_level) + 1}"
            )
            for i in range(total_requests)
        ]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    total_time_sec = time.perf_counter() - overall_start

    latencies = [r["latency_ms"] for r in results]
    successes = sum(1 for r in results if r["success"])
    latencies.sort()

    p50 = statistics.median(latencies)
    p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0.0
    p99 = latencies[int(len(latencies) * 0.99)] if latencies else 0.0
    rps = total_requests / total_time_sec if total_time_sec > 0 else 0.0

    return {
        "concurrency": concurrency_level,
        "total_requests": total_requests,
        "success_count": successes,
        "error_count": total_requests - successes,
        "rps": round(rps, 1),
        "min_ms": round(min(latencies), 2),
        "mean_ms": round(statistics.mean(latencies), 2),
        "p50_ms": round(p50, 2),
        "p95_ms": round(p95, 2),
        "p99_ms": round(p99, 2),
        "max_ms": round(max(latencies), 2),
        "total_time_sec": round(total_time_sec, 3)
    }


def main():
    print("=" * 80)
    print("MEDDATA AI FASTAPI -- IN-PROCESS ASGI CONCURRENCY DISPATCH BENCHMARK")
    print("=" * 80)
    print("Testing In-Process ASGI Dispatch (In-Memory Function Calls) Across Concurrency Levels (10, 50, 100 workers)\n")

    tiers = [
        (10, 100),
        (50, 250),
        (100, 500)
    ]

    tier_results = []
    for concurrency, num_requests in tiers:
        print(f"[*] Running Benchmark Tier: {concurrency} Concurrent Workers ({num_requests} total requests)...")
        res = run_concurrency_tier(concurrency, num_requests)
        tier_results.append(res)

    print("\n" + "=" * 80)
    print(f"{'Concurrency':<12} | {'Requests':<10} | {'RPS':<10} | {'p50 (ms)':<10} | {'p95 (ms)':<10} | {'p99 (ms)':<10} | {'Success Rate'}")
    print("-" * 80)
    for r in tier_results:
        pct = (r["success_count"] / r["total_requests"]) * 100
        print(f"{r['concurrency']:<12} | {r['total_requests']:<10} | {r['rps']:<10} | {r['p50_ms']:<10} | {r['p95_ms']:<10} | {r['p99_ms']:<10} | {pct:.1f}%")
    print("=" * 80)


if __name__ == "__main__":
    main()
