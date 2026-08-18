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
    """Runs a dedicated security test battery on the SQL Sandbox validator."""
    test_queries = [
        ("SELECT * FROM Doctors;", True, "Simple safe SELECT"),
        ("SELECT specialty, COUNT(*) FROM Doctors GROUP BY specialty;", True, "Aggregate SELECT"),
        ("WITH TopDocs AS (SELECT * FROM Doctors) SELECT * FROM TopDocs;", True, "CTE Read-only"),
        ("DROP TABLE Doctors;", False, "Malicious DROP TABLE"),
        ("DELETE FROM Doctors WHERE id = 1;", False, "Malicious DELETE"),
        ("UPDATE Doctors SET consultation_fee = 0;", False, "Malicious UPDATE"),
        ("INSERT INTO Doctors (name) VALUES ('Hacked');", False, "Malicious INSERT"),
        ("PRAGMA table_info(Doctors);", False, "Administrative PRAGMA"),
        ("SELECT * FROM Doctors; DROP TABLE Doctors;", False, "Multi-statement injection"),
        ("ALTER TABLE Doctors ADD COLUMN secret TEXT;", False, "DDL ALTER TABLE")
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
    print("=" * 70)

    return passed_count == total_count and sandbox_res["all_passed"]


if __name__ == "__main__":
    success = print_cli_test_report()
    sys.exit(0 if success else 1)
