"""
Unit and Negative-Path Tests for Bounded LLM Parsing & Security Sandbox
========================================================================
Tests failure modes, malformed JSON recovery, API timeouts, HTTP 500 errors,
pre-LLM safety checks, and strict SQL sandbox table/catalog defenses.
"""

import pytest
from unittest.mock import patch, MagicMock
from models import IntentType, DomainType
from llm_parser import parse_intent_with_llm
from intent_parser import parse_user_intent_hybrid
from safety import validate_sql_sandbox_query


def test_llm_parser_malformed_json_fallback():
    """Verifies that an LLM returning garbage/malformed JSON safely falls back without crashing."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [{
            "content": {
                "parts": [{"text": "```json\n{ this is not valid json: invalid\n```"}]
            }
        }]
    }

    with patch("requests.post", return_value=mock_resp):
        res, latency, err = parse_intent_with_llm(
            "Find a cardiologist in Chennai under 1500",
            api_key="AIzaSyTestMockKey123",
            provider="gemini"
        )
        assert res is None
        assert err is not None
        assert "fail" in err.lower() or "json" in err.lower() or "expecting" in err.lower()


def test_llm_parser_http_500_fallback():
    """Verifies that an HTTP 500 server error from LLM provider triggers clean fallback."""
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "Internal Server Error"

    with patch("requests.post", return_value=mock_resp):
        res, latency, err = parse_intent_with_llm(
            "Find a cardiologist in Chennai under 1500",
            api_key="AIzaSyTestMockKey123",
            provider="gemini"
        )
        assert res is None
        assert "500" in str(err)


def test_llm_parser_network_timeout_fallback():
    """Verifies that a network timeout triggers graceful degradation to deterministic parser."""
    with patch("requests.post", side_effect=TimeoutError("Request timed out")):
        res, latency, err = parse_intent_with_llm(
            "Find a cardiologist in Chennai under 1500",
            api_key="AIzaSyTestMockKey123",
            provider="gemini"
        )
        assert res is None
        assert "timed out" in str(err).lower() or "error" in str(err).lower()


def test_hybrid_parser_degrades_gracefully_on_llm_failure():
    """Verifies that parse_user_intent_hybrid seamlessly falls back to deterministic AST parser."""
    with patch("llm_parser.parse_intent_with_llm", return_value=(None, 10.0, "Mocked API Timeout")):
        res, engine_used, latency = parse_user_intent_hybrid(
            "Find a cardiologist in Chennai under 1500 available today",
            engine="llm",
            api_key="AIzaSyTestMockKey123",
            provider="gemini"
        )
        # Should fall back to deterministic and still extract Cardiology correctly
        assert res is not None
        assert res.intent in [IntentType.DOCTOR_SEARCH, IntentType.AFFORDABILITY, IntentType.AVAILABILITY]
        assert "Deterministic" in engine_used
        assert res.filters is not None
        assert res.filters.specialty.value == "Cardiology"


def test_sql_sandbox_blocks_sqlite_master_schema_leak():
    """Security regression test: Verifies that sqlite_master and sqlite_schema cannot be read."""
    queries = [
        "SELECT sql FROM sqlite_master WHERE type='table';",
        "SELECT * FROM sqlite_schema;",
        "SELECT name FROM sqlite_temp_master;",
        "SELECT * FROM sqlite_sequence;"
    ]
    for q in queries:
        is_safe, decision = validate_sql_sandbox_query(q)
        assert is_safe is False
        assert "Security Violation" in decision or "forbidden" in decision or "restricted" in decision


def test_sql_sandbox_blocks_recursive_cte_dos():
    """Security regression test: Verifies that recursive CTEs (DoS vectors) are blocked."""
    recursive_query = "WITH RECURSIVE cnt(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM cnt WHERE x<1000000) SELECT count(*) FROM cnt;"
    is_safe, decision = validate_sql_sandbox_query(recursive_query)
    assert is_safe is False
    assert "RECURSIVE" in decision or "Security Violation" in decision


def test_sql_sandbox_blocks_unauthorized_tables():
    """Security regression test: Verifies that non-allowlisted tables cannot be queried."""
    unauthorized_query = "SELECT * FROM Users;"
    is_safe, decision = validate_sql_sandbox_query(unauthorized_query)
    assert is_safe is False
    assert "not in the sandbox allowlist" in decision or "Security Violation" in decision
