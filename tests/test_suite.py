"""
MedData AI - Automated Test Suite & Runner
Executes comprehensive validation tests against intent classification, entity extraction,
safety guardrails, deterministic SQL query building, and database grounding.
"""

import time
import sys
from typing import List, Dict, Any

from models import TestCase, TestCaseResult, IntentType
from intent_parser import parse_intent_and_filters
from query_engine import execute_doctor_search, execute_housing_search, build_safe_query
from database import init_database, get_connection
from safety import validate_sql_sandbox_query
from tests.test_cases import ALL_TEST_CASES


def run_single_test(test_case: TestCase) -> TestCaseResult:
    """Executes a single test case through the end-to-end processing pipeline."""
    start_time = time.perf_counter()
    failures: List[str] = []

    # 1. Parse prompt through NLP & Safety layer
    classification = parse_intent_and_filters(test_case.input_prompt)
    
    # 2. Check Intent
    if classification.intent != test_case.expected_intent:
        failures.append(
            f"Expected intent '{test_case.expected_intent.value}', got '{classification.intent.value}'."
        )

    # 3. Check Ambiguity
    if test_case.expected_ambiguity != classification.ambiguity_detected:
        failures.append(
            f"Expected ambiguity={test_case.expected_ambiguity}, got {classification.ambiguity_detected}."
        )

    # 4. Check Specialty Filter
    actual_spec = classification.filters.specialty.value if classification.filters.specialty else None
    expected_spec = test_case.expected_specialty.value if test_case.expected_specialty else None
    
    if expected_spec != actual_spec:
        failures.append(
            f"Expected specialty '{expected_spec}', got '{actual_spec}'."
        )

    # 5. Check Safety Refusal
    if test_case.expected_safety_refusal:
        if classification.intent not in [IntentType.MEDICAL_ADVICE, IntentType.PROMPT_INJECTION]:
            failures.append("Expected safety refusal but query was not blocked.")

    # 6. Check Unknown Attribute
    if test_case.expected_unknown_attribute:
        if classification.intent != IntentType.UNKNOWN_ATTRIBUTE:
            failures.append("Expected unknown attribute refusal.")

    # 7. Check Contradiction
    if test_case.expected_contradiction:
        if classification.intent != IntentType.CONTRADICTION:
            failures.append("Expected contradiction detection.")

    # 8. Query execution & result count check (if query is valid executable search)
    actual_sql = ""
    actual_params = []
    result_count = 0

    if classification.intent == IntentType.HOUSING_SEARCH and classification.housing_filters:
        query_res = execute_housing_search(classification.housing_filters)
        actual_sql = query_res.sql_template
        actual_params = query_res.params
        result_count = query_res.row_count

        if result_count < test_case.expected_min_results:
            failures.append(
                f"Expected at least {test_case.expected_min_results} properties, got {result_count}."
            )
    elif classification.intent in [IntentType.DOCTOR_SEARCH, IntentType.DIRECTORY, IntentType.AFFORDABILITY, IntentType.DISTANCE, IntentType.AVAILABILITY, IntentType.RANKING]:
        query_res = execute_doctor_search(classification.filters)
        actual_sql = query_res.sql_template
        actual_params = query_res.params
        result_count = query_res.row_count

        if result_count < test_case.expected_min_results:
            failures.append(
                f"Expected at least {test_case.expected_min_results} results, got {result_count}."
            )

    exec_time = round((time.perf_counter() - start_time) * 1000, 2)
    passed = len(failures) == 0

    return TestCaseResult(
        test_case=test_case,
        actual_intent=classification.intent,
        actual_ambiguity=classification.ambiguity_detected,
        actual_specialty=actual_spec,
        actual_sql=actual_sql,
        actual_params=actual_params,
        result_count=result_count,
        passed=passed,
        failure_reasons=failures,
        execution_time_ms=exec_time
    )


def run_all_tests(test_cases: List[TestCase] = ALL_TEST_CASES) -> List[TestCaseResult]:
    """Runs all automated test cases and returns structured results."""
    init_database(force_reset=True)  # Ensure database is freshly prepared
    results = []
    for tc in test_cases:
        res = run_single_test(tc)
        results.append(res)
    return results


def run_sql_sandbox_security_tests() -> Dict[str, Any]:
    """Runs a dedicated security test battery on the SQL Sandbox AST validator."""
    test_queries = [
        ("SELECT * FROM Doctors;", True, "Simple safe SELECT"),
        ("SELECT specialty, COUNT(*) FROM Doctors GROUP BY specialty;", True, "Aggregate SELECT"),
        ("WITH TopDocs AS (SELECT * FROM Doctors) SELECT * FROM TopDocs;", True, "CTE Read-only"),
        ("SELECT * FROM main.Doctors;", True, "Schema-qualified allowed table"),
        ("SELECT * FROM doctors WHERE specialty = 'Cardiology';", True, "Case-insensitive table"),
        ("EXPLAIN QUERY PLAN SELECT * FROM Doctors WHERE city = 'Chennai';", True, "EXPLAIN on valid SELECT"),
        ("DROP TABLE Doctors;", False, "Malicious DROP TABLE"),
        ("DELETE FROM Doctors WHERE id = 1;", False, "Malicious DELETE"),
        ("UPDATE Doctors SET consultation_fee = 0;", False, "Malicious UPDATE"),
        ("INSERT INTO Doctors (name) VALUES ('Hacked');", False, "Malicious INSERT"),
        ("PRAGMA table_info(Doctors);", False, "Administrative PRAGMA"),
        ("SELECT * FROM Doctors; DROP TABLE Doctors;", False, "Multi-statement injection"),
        ("ALTER TABLE Doctors ADD COLUMN secret TEXT;", False, "DDL ALTER TABLE"),
        ("SELECT * FROM sqlite_master;", False, "System catalog sqlite_master"),
        ("SELECT * FROM sqlite_schema;", False, "System catalog sqlite_schema"),
        ("SELECT * FROM main.sqlite_master;", False, "Schema-qualified system catalog"),
        ("WITH x AS (SELECT 1) SELECT * FROM RandomTable;", False, "CTE with unlisted table"),
        ("WITH a AS (SELECT 1), b AS (SELECT * FROM RandomTable) SELECT * FROM a,b;", False, "Multi-CTE with unlisted table"),
        ("SELECT * FROM Doctors, RandomTable;", False, "Comma join with unlisted table"),
        ("SELECT * FROM Doctors JOIN RandomTable ON Doctors.id = RandomTable.id;", False, "Explicit JOIN with unlisted table"),
        ("SELECT * FROM Doctors WHERE id IN (SELECT id FROM RandomTable);", False, "Subquery with unlisted table"),
        ("WITH RECURSIVE cnt(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM cnt) SELECT count(*) FROM cnt;", False, "Recursive CTE DoS"),
        ("SELECT * FROM Doctors UNION SELECT sql, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 FROM sqlite_master;", False, "UNION with system catalog"),
        ("EXPLAIN DROP TABLE Doctors;", False, "EXPLAIN-wrapped DROP mutation"),
        ("EXPLAIN QUERY PLAN DELETE FROM Doctors;", False, "EXPLAIN QUERY PLAN DELETE mutation"),
        ("EXPLAIN SELECT * FROM RandomTable;", False, "EXPLAIN with unlisted table"),
    ]

    passed_count = 0
    details = []
    for query, should_pass, desc in test_queries:
        is_safe, reason = validate_sql_sandbox_query(query)
        passed = (is_safe == should_pass)
        if passed:
            passed_count += 1
        details.append({
            "query": query,
            "description": desc,
            "expected_safe": should_pass,
            "actual_safe": is_safe,
            "passed": passed,
            "reason": reason
        })

    return {
        "total": len(test_queries),
        "passed": passed_count,
        "all_passed": (passed_count == len(test_queries)),
        "details": details
    }


def run_query_cache_tests() -> Dict[str, Any]:
    """Runs functional tests verifying LRU caching, TTL expiration, schema drift flush, and emergency bypass."""
    from query_cache import QueryCache, CachedQueryPlan, normalize_query, compile_and_validate_query_with_cache
    
    cache_tests = []
    
    # 1. Normalization
    n_pass = (normalize_query("  FIND a Cardiologist?  ") == "find a cardiologist")
    cache_tests.append(("Query Normalization", n_pass, "Normalizes casing, whitespace, and punctuation"))
    
    # 2. Cache Hit
    cache = QueryCache(max_size=5, ttl_seconds=60)
    q = "Find a cardiologist in Chennai"
    plan1, hit1, _ = compile_and_validate_query_with_cache(q, use_cache=True, cache_instance=cache)
    plan2, hit2, _ = compile_and_validate_query_with_cache(q, use_cache=True, cache_instance=cache)
    hit_pass = (not hit1) and hit2 and (plan1.sql_template == plan2.sql_template)
    cache_tests.append(("Cache Hit & Retrieval", hit_pass, "Returns identical SQL on hit without re-parsing"))
    
    # 3. TTL Expiry
    short_cache = QueryCache(max_size=5, ttl_seconds=0.05)
    short_cache.put(q, plan1)
    time.sleep(0.08)
    exp_pass = (short_cache.get(q) is None and short_cache.stats["expirations"] == 1)
    cache_tests.append(("TTL Expiration", exp_pass, "Stale entries automatically expire and miss after TTL"))
    
    # 4. Schema Drift Flush
    schema_cache = QueryCache(max_size=5, ttl_seconds=60, schema_check_interval_seconds=0.0)
    schema_cache.put(q, plan1)
    conn = get_connection()
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS _cache_test_schema (id INT);")
        conn.commit()
    finally:
        conn.close()
    drift_pass = (schema_cache.get(q) is None and schema_cache.stats["schema_invalidations"] == 1)
    conn = get_connection()
    try:
        conn.execute("DROP TABLE IF EXISTS _cache_test_schema;")
        conn.commit()
    finally:
        conn.close()
    cache_tests.append(("Schema Invalidation", drift_pass, "Flushes entire cache when sqlite_master changes"))
    
    # 5. Emergency Query Bypass
    em_cache = QueryCache(max_size=5, ttl_seconds=60)
    em_q = "I am having a heart attack and cannot breathe"
    em_plan, em_hit, _ = compile_and_validate_query_with_cache(em_q, use_cache=True, cache_instance=em_cache)
    em_pass = (len(em_cache._cache) == 0 and em_cache.stats["bypasses"] == 1 and em_cache.get(em_q) is None)
    cache_tests.append(("Emergency Query Bypass", em_pass, "Acute healthcare emergencies strictly bypass cache"))
    
    # 6. LRU Eviction
    lru_cache = QueryCache(max_size=2, ttl_seconds=60)
    lru_cache.put("Q1", plan1)
    lru_cache.put("Q2", plan1)
    lru_cache.get("Q1")  # Q2 is now LRU
    lru_cache.put("Q3", plan1)
    lru_pass = (lru_cache.get("Q2") is None and lru_cache.get("Q1") is not None and lru_cache.stats["evictions"] == 1)
    cache_tests.append(("LRU Eviction Policy", lru_pass, "Least recently used entry evicted when max capacity reached"))

    passed_count = sum(1 for _, p, _ in cache_tests if p)
    return {
        "total": len(cache_tests),
        "passed": passed_count,
        "all_passed": (passed_count == len(cache_tests)),
        "details": [{"name": n, "passed": p, "description": d} for n, p, d in cache_tests]
    }


def print_cli_test_report():
    """Runs all test suites and prints a formatted report to console."""
    print("=" * 70)
    print("MEDDATA AI AGENT -- COMPREHENSIVE VERIFICATION SUITE")
    print("=" * 70)

    results = run_all_tests()
    passed_count = sum(1 for r in results if r.passed)
    total_count = len(results)

    for r in results:
        status = "[PASS]" if r.passed else "[FAIL]"
        tc = r.test_case
        print(f"{status} {tc.id} ({tc.category}): {tc.input_prompt}")
        if not r.passed:
            for reason in r.failure_reasons:
                print(f"       -> {reason}")

    print("\n" + "-" * 70)
    print(f"SUMMARY: {passed_count}/{total_count} Tests Passed ({round((passed_count/total_count)*100, 1)}%)")
    
    # Run SQL security tests
    sandbox_res = run_sql_sandbox_security_tests()
    print(f"SQL Sandbox Security Tests: {sandbox_res['passed']}/{sandbox_res['total']} Passed")

    # Run Query Cache tests
    cache_res = run_query_cache_tests()
    print(f"Query Cache & Invalidation Tests: {cache_res['passed']}/{cache_res['total']} Passed")
    print("=" * 70)

    return passed_count == total_count and sandbox_res["all_passed"] and cache_res["all_passed"]


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    success = print_cli_test_report()
    sys.exit(0 if success else 1)

