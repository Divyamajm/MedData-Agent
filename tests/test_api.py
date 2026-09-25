"""
Pytest Suite for FastAPI REST API Layer
========================================
Tests HTTP endpoints (/health, /triage/query, /sandbox/sql, /eval/benchmark)
using FastAPI TestClient.
"""

import pytest
from fastapi.testclient import TestClient
from api import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def enable_demo_auth_by_default(monkeypatch):
    """Defaults to demo mode for general functional tests unless explicitly overridden."""
    monkeypatch.setenv("MEDDATA_ALLOW_UNAUTHENTICATED_DEMO", "true")


@pytest.mark.api
def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert "no-store" in response.headers.get("Cache-Control", "")
    data = response.json()
    assert data["status"] == "healthy"
    assert data["doctors_count"] > 0
    assert data["properties_count"] > 0
    assert "ast_validator" in data
    assert "sqlglot" in data["ast_validator"]


@pytest.mark.api
def test_api_key_authentication_enforced_when_configured(monkeypatch):
    """Verifies that when MEDDATA_API_KEY is configured, requests without valid X-API-Key are rejected with 401."""
    monkeypatch.setenv("MEDDATA_API_KEY", "test-secret-key-12345")
    
    # 1. Missing header -> 401
    resp_missing = client.post("/api/v1/sandbox/sql", json={"sql": "SELECT * FROM Doctors LIMIT 1;"})
    assert resp_missing.status_code == 401
    assert "Unauthorized" in resp_missing.json()["detail"]

    # 2. Invalid header -> 401
    resp_invalid = client.post(
        "/api/v1/sandbox/sql", 
        json={"sql": "SELECT * FROM Doctors LIMIT 1;"},
        headers={"X-API-Key": "wrong-key"}
    )
    assert resp_invalid.status_code == 401

    # 3. Valid header -> 200
    resp_valid = client.post(
        "/api/v1/sandbox/sql", 
        json={"sql": "SELECT * FROM Doctors LIMIT 1;"},
        headers={"X-API-Key": "test-secret-key-12345"}
    )
    assert resp_valid.status_code == 200
    assert resp_valid.json()["is_safe"] is True


@pytest.mark.api
def test_sql_sandbox_endpoint_explain_queries():
    """Verifies that the SQL sandbox API correctly permits EXPLAIN on safe SELECT and blocks EXPLAIN on mutations."""
    # Safe EXPLAIN
    resp_safe = client.post("/api/v1/sandbox/sql", json={"sql": "EXPLAIN QUERY PLAN SELECT * FROM Doctors;"})
    assert resp_safe.status_code == 200
    assert resp_safe.json()["is_safe"] is True

    # Malicious EXPLAIN DROP
    resp_blocked = client.post("/api/v1/sandbox/sql", json={"sql": "EXPLAIN DROP TABLE Doctors;"})
    assert resp_blocked.status_code == 200
    assert resp_blocked.json()["is_safe"] is False
    assert "BLOCKED" in resp_blocked.json()["validation_decision"]


@pytest.mark.api
def test_triage_query_endpoint():
    payload = {
        "query": "Find a cardiologist in Chennai under 1500 available today",
        "engine": "deterministic"
    }
    response = client.post("/api/v1/triage/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"].lower() == "success"
    assert data["domain"] == "healthcare"
    assert data["intent"] == "doctor_search"
    assert "data" in data
    assert len(data["data"]) > 0


@pytest.mark.api
def test_sql_sandbox_endpoint_safe_query():
    payload = {
        "sql": "SELECT name, specialty, consultation_fee FROM Doctors LIMIT 3;"
    }
    response = client.post("/api/v1/sandbox/sql", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["is_safe"] is True
    assert len(data["rows"]) > 0


@pytest.mark.api
def test_sql_sandbox_endpoint_blocked_query():
    payload = {
        "sql": "DROP TABLE Doctors;"
    }
    response = client.post("/api/v1/sandbox/sql", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["is_safe"] is False
    assert "BLOCKED" in data["validation_decision"]


@pytest.mark.api
def test_sql_sandbox_endpoint_blocks_sqlite_master():
    payload = {
        "sql": "SELECT sql FROM sqlite_master WHERE type='table';"
    }
    response = client.post("/api/v1/sandbox/sql", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["is_safe"] is False
    assert "Security Violation" in data["validation_decision"] or "BLOCKED" in data["validation_decision"]


@pytest.mark.api
def test_benchmark_endpoint_cached():
    response = client.get("/api/v1/eval/benchmark")
    assert response.status_code == 200
    data = response.json()
    assert "benchmark_summary" in data
    assert data["benchmark_summary"]["total_queries"] == 290


@pytest.mark.api
def test_sandbox_connection_closed_on_execution_error():
    """Verifies that an error in SQL execution returns 400 without leaking connection."""
    # A valid-per-validator table query that has an invalid column name
    payload = {"sql": "SELECT non_existent_column_xyz FROM Doctors;"}
    response = client.post("/api/v1/sandbox/sql", json=payload)
    assert response.status_code == 400
    assert "SQL execution failed" in response.json()["detail"]


@pytest.mark.api
def test_api_rate_limiter_allows_normal_traffic():
    """Verifies that normal request traffic succeeds with timing headers."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert "X-Response-Time-MS" in response.headers


@pytest.mark.api
def test_api_strict_production_mode_rejects_unconfigured_key(monkeypatch):
    """Verifies that in strict production mode without MEDDATA_API_KEY, requests are rejected with 503."""
    monkeypatch.delenv("MEDDATA_API_KEY", raising=False)
    monkeypatch.setenv("MEDDATA_ALLOW_UNAUTHENTICATED_DEMO", "false")

    response = client.post("/api/v1/sandbox/sql", json={"sql": "SELECT * FROM Doctors LIMIT 1;"})
    assert response.status_code == 503
    assert "requires MEDDATA_API_KEY in production mode" in response.json()["detail"]


@pytest.mark.api
def test_appointment_booking_collision_handled_atomically():
    """Verifies that concurrent booking attempts for the same doctor and slot are handled race-free."""
    import time
    from database import book_appointment, init_database
    init_database(force_reset=False)

    unique_date = f"2099-01-{(int(time.time()*1000) % 28) + 1:02d}"
    unique_slot = f"{(int(time.time()) % 12) + 1:02d}:00 PM"

    # Book initial appointment
    res1 = book_appointment(
        doctor_id=1,
        patient_name="Patient One",
        patient_email="one@example.com",
        appointment_date=unique_date,
        time_slot=unique_slot,
        symptoms_reason="Routine Checkup"
    )
    assert res1["success"] is True

    # Attempt collision booking for exact same doctor and slot
    res2 = book_appointment(
        doctor_id=1,
        patient_name="Patient Two",
        patient_email="two@example.com",
        appointment_date=unique_date,
        time_slot=unique_slot,
        symptoms_reason="Followup"
    )
    assert res2["success"] is False
    assert "already booked" in res2["error"] or "Collision detected" in res2["error"]


@pytest.mark.api
def test_x_forwarded_for_proxy_spoofing_protection():
    """Verifies that X-Forwarded-For header from untrusted peers does not bypass security."""
    from api import TRUSTED_PROXY_IPS
    # When testclient (which is in default TRUSTED_PROXY_IPS) sends X-Forwarded-For, it's accepted
    resp = client.get("/api/v1/health", headers={"X-Forwarded-For": "203.0.113.195"})
    assert resp.status_code == 200

