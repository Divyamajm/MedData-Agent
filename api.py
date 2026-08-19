"""
MedData AI -- Production FastAPI REST Service Layer
====================================================
Provides OpenAPI-documented REST endpoints for natural language clinical/housing discovery,
intent extraction, SQL sandbox security validation, and automated AI evaluation benchmarks.

Run via: python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload
"""

import os
import time
import uuid
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Query, Header, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from models import (
    IntentType, DomainType, CanonicalSpecialty,
    SearchFilters, HousingSearchFilters, IntentClassificationResult
)
from intent_parser import parse_user_intent_hybrid
from query_engine import execute_doctor_search, execute_housing_search
from database import init_database, get_connection
from safety import validate_sql_sandbox_query
from tests.eval_benchmark import run_full_evaluation_benchmark

# Initialize Database
init_database(force_reset=False)

app = FastAPI(
    title="MedData AI & UrbanLocate REST API",
    description="Deterministic Grounded Healthcare & Housing Discovery Engine with Token-Validated SQL Sandboxing & Bounded LLM Intent Parsing.",
    version="1.0.0",
    contact={
        "name": "Divyam Sharma",
        "email": "divyamajm@gmail.com",
        "url": "https://github.com/Divyamajm/MedData-Agent"
    }
)

# Standardized CORS Configuration (No wildcard with credentials)
ALLOWED_ORIGINS = [
    "http://localhost:8501",
    "http://localhost:8000",
    "http://localhost:3000",
    "http://127.0.0.1:8501",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:3000",
    "https://meddata-divyam.streamlit.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# Structured Request ID & Timing Middleware
@app.middleware("http")
async def add_request_metadata(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    start_time = time.perf_counter()
    response: Response = await call_next(request)
    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time-MS"] = str(duration_ms)
    return response


# ==========================================
# 📥 REQUEST & RESPONSE SCHEMAS
# ==========================================

class TriageQueryRequest(BaseModel):
    query: str = Field(
        ..., 
        json_schema_extra={"example": "Find a cardiologist in Chennai under ₹1500 available today"}, 
        description="Natural language search query"
    )
    engine: str = Field(
        default="deterministic", 
        json_schema_extra={"example": "deterministic"}, 
        description="'deterministic' (<3ms regex) or 'llm' (Gemini/OpenAI) or 'auto'"
    )
    api_key: Optional[str] = Field(
        default=None, 
        description="Optional client-supplied API key; defaults to server environment variable"
    )
    provider: Optional[str] = Field(
        default="gemini", 
        description="LLM provider ('gemini' or 'openai')"
    )


class TriageQueryResponse(BaseModel):
    status: str
    raw_query: str
    domain: str
    intent: str
    engine_used: str
    ambiguity_detected: bool
    clarification_options: Optional[List[str]] = None
    explanation: Optional[str] = None
    sql_executed: Optional[str] = None
    params: Optional[List[Any]] = None
    row_count: int
    data: List[Dict[str, Any]]
    execution_time_ms: float


class SQLSandboxRequest(BaseModel):
    sql: str = Field(
        ..., 
        json_schema_extra={"example": "SELECT name, specialty, consultation_fee FROM Doctors WHERE consultation_fee < 1000 ORDER BY consultation_fee ASC LIMIT 10;"}, 
        description="SQL query to validate and execute in read-only sandbox"
    )


class SQLSandboxResponse(BaseModel):
    is_safe: bool
    validation_decision: str
    row_count: int
    columns: List[str]
    rows: List[Dict[str, Any]]
    execution_time_ms: float


# Benchmark In-Memory Cache (Prevents CPU exhaustion DoS)
_BENCHMARK_CACHE: Dict[str, Any] = {
    "timestamp": 0.0,
    "data": None
}


# ==========================================
# 🚀 API ENDPOINTS
# ==========================================

@app.get("/", tags=["General"])
def root():
    return {
        "service": "MedData AI & UrbanLocate API",
        "version": "1.0.0",
        "author": "Divyam Sharma",
        "docs_url": "/docs",
        "architecture": "Deterministic Grounded Intent Parser with Bounded LLM Fallback",
        "endpoints": {
            "query_triage": "POST /api/v1/triage/query",
            "sql_sandbox": "POST /api/v1/sandbox/sql",
            "benchmark_metrics": "GET /api/v1/eval/benchmark",
            "health": "GET /api/v1/health"
        }
    }


@app.get("/api/v1/health", tags=["General"])
def health_check():
    """Returns database connectivity, WAL mode status, and record counts."""
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM Doctors;")
        doc_count = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM Properties;")
        prop_count = c.fetchone()[0]
        c.execute("PRAGMA journal_mode;")
        journal_mode = c.fetchone()[0]
        conn.close()
        return {
            "status": "healthy",
            "database": "SQLite (hospital_ultimate.db)",
            "journal_mode": str(journal_mode).upper(),
            "doctors_count": doc_count,
            "properties_count": prop_count,
            "uptime": "100%"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="Database health check failed.")


@app.post("/api/v1/triage/query", response_model=TriageQueryResponse, tags=["Discovery & Triage"])
def process_triage_query(payload: TriageQueryRequest):
    """
    Executes the Dual-Engine Triage Pipeline:
    1. Parses natural language intent (Deterministic Regex or Bounded LLM)
    2. Runs Safety Guardrails (Emergency, Prescription Refusal, Unknown Field, Prompt Injection)
    3. Executes Parameterized Read-Only SQL against ground-truth database
    """
    start_time = time.perf_counter()
    
    # Resolve server-side key if not provided by client
    resolved_api_key = payload.api_key or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")

    # Intent extraction
    classification, engine_used, parse_lat = parse_user_intent_hybrid(
        payload.query,
        engine=payload.engine,
        api_key=resolved_api_key,
        provider=payload.provider
    )

    # Intercept Safety / Refusal Intents
    if classification.intent in [
        IntentType.EMERGENCY,
        IntentType.MEDICAL_ADVICE,
        IntentType.UNKNOWN_ATTRIBUTE,
        IntentType.PROMPT_INJECTION
    ]:
        lat = round((time.perf_counter() - start_time) * 1000, 2)
        return TriageQueryResponse(
            status="safety_intercepted",
            raw_query=payload.query,
            domain=classification.domain.value,
            intent=classification.intent.value,
            engine_used=engine_used,
            ambiguity_detected=False,
            explanation=classification.explanation,
            row_count=0,
            data=[],
            execution_time_ms=lat
        )

    # Intercept Ambiguity
    if classification.ambiguity_detected:
        lat = round((time.perf_counter() - start_time) * 1000, 2)
        return TriageQueryResponse(
            status="ambiguity_intercepted",
            raw_query=payload.query,
            domain=classification.domain.value,
            intent=classification.intent.value,
            engine_used=engine_used,
            ambiguity_detected=True,
            clarification_options=classification.clarification_options,
            explanation=classification.explanation,
            row_count=0,
            data=[],
            execution_time_ms=lat
        )

    # Execute Search
    sql_executed = None
    params = []
    rows = []
    
    if classification.domain == DomainType.REAL_ESTATE:
        h_res = execute_housing_search(classification.housing_filters or HousingSearchFilters())
        sql_executed = h_res.sql_template
        params = h_res.params
        rows = h_res.data
    else:
        q_res = execute_doctor_search(classification.filters or SearchFilters())
        sql_executed = q_res.sql_template
        params = q_res.params
        rows = q_res.data

    total_latency = round((time.perf_counter() - start_time) * 1000, 2)

    return TriageQueryResponse(
        status="success",
        raw_query=payload.query,
        domain=classification.domain.value,
        intent=classification.intent.value,
        engine_used=engine_used,
        ambiguity_detected=False,
        explanation=classification.explanation,
        sql_executed=sql_executed,
        params=params,
        row_count=len(rows),
        data=rows,
        execution_time_ms=total_latency
    )


@app.post("/api/v1/sandbox/sql", response_model=SQLSandboxResponse, tags=["Security & Sandbox"])
def execute_sql_sandbox(payload: SQLSandboxRequest):
    """
    Validates an ad-hoc SQL query through the 2-layer token and table sandbox:
    - Layer 1: First-token allowlist (SELECT, WITH, EXPLAIN) + Mutation Blocklist
    - Layer 2: Table allowlist (Doctors, Properties, Appointments, Specialties) + System Catalog Blocklist
    - Execution Guardrail: Enforces max 100-row cap and instruction step limits to prevent DoS.
    """
    start_time = time.perf_counter()
    is_safe, decision = validate_sql_sandbox_query(payload.sql)
    
    if not is_safe:
        lat = round((time.perf_counter() - start_time) * 1000, 2)
        return SQLSandboxResponse(
            is_safe=False,
            validation_decision=f"🚫 BLOCKED: {decision}",
            row_count=0,
            columns=[],
            rows=[],
            execution_time_ms=lat
        )

    try:
        conn = get_connection()
        conn.row_factory = None
        
        # Guardrail: Prevent runaway CPU execution with progress handler (max 200,000 steps)
        step_count = 0
        def step_monitor():
            nonlocal step_count
            step_count += 1
            if step_count > 1000:
                return 1 # Abort query execution
            return 0

        conn.set_progress_handler(step_monitor, 200)

        c = conn.cursor()
        c.execute(payload.sql)
        columns = [desc[0] for desc in c.description] if c.description else []
        # Enforce maximum 100 rows returned from sandbox
        raw_rows = c.fetchmany(100)
        conn.close()

        dict_rows = [dict(zip(columns, r)) for r in raw_rows]
        lat = round((time.perf_counter() - start_time) * 1000, 2)

        return SQLSandboxResponse(
            is_safe=True,
            validation_decision="🛡️ SAFE READ-ONLY QUERY (Token & Table Validated)",
            row_count=len(dict_rows),
            columns=columns,
            rows=dict_rows,
            execution_time_ms=lat
        )
    except Exception as e:
        lat = round((time.perf_counter() - start_time) * 1000, 2)
        # Sanitize exception message so internal database paths/structures are not exposed
        raise HTTPException(
            status_code=400, 
            detail="SQL execution failed. Please verify syntax, column names, and table references."
        )


@app.get("/api/v1/eval/benchmark", tags=["AI & Testing Benchmarks"])
def get_evaluation_benchmark_metrics(
    engine: str = Query(default="deterministic", description="Engine to evaluate: 'deterministic' or 'llm'"),
    force_refresh: bool = Query(default=False, description="Bypass cache and recompute full 290-query benchmark")
):
    """
    Returns the 290-query scientific evaluation benchmark metrics.
    Includes in-memory caching to prevent resource exhaustion.
    """
    global _BENCHMARK_CACHE
    now = time.time()

    # Cache benchmark result for 60 seconds unless forced
    if not force_refresh and _BENCHMARK_CACHE["data"] is not None and (now - _BENCHMARK_CACHE["timestamp"]) < 60:
        return _BENCHMARK_CACHE["data"]

    report = run_full_evaluation_benchmark(engine=engine)
    result = {
        "benchmark_summary": {
            "total_queries": report.total_cases,
            "intent_accuracy_pct": report.intent_accuracy_pct,
            "entity_precision_pct": report.entity_precision_pct,
            "safety_refusal_precision_pct": report.safety_refusal_precision_pct,
            "safety_refusal_recall_pct": report.safety_refusal_recall_pct,
            "ambiguity_interception_pct": report.ambiguity_interception_pct,
            "sql_execution_success_pct": report.sql_execution_success_pct,
            "latency_p50_ms": report.p50_latency_ms,
            "latency_p95_ms": report.p95_latency_ms,
            "latency_p99_ms": report.p99_latency_ms,
            "latency_mean_ms": report.avg_latency_ms
        },
        "category_summary": report.category_summary,
        "sample_detailed_cases": report.detailed_results[:10]
    }

    _BENCHMARK_CACHE["timestamp"] = now
    _BENCHMARK_CACHE["data"] = result
    return result
