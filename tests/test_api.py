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


@pytest.mark.api
def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["doctors_count"] > 0
    assert data["properties_count"] > 0


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
    assert "BLOCKED" in data["validation_decision"].upper() or "MUTATION" in data["validation_decision"].upper()
