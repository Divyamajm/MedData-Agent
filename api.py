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
from fastapi import FastAPI, HTTPException, Query, Header, Request, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from models import (
    IntentType, DomainType, CanonicalSpecialty,
    SearchFilters, HousingSearchFilters, IntentClassificationResult
)
from intent_parser import parse_user_intent_hybrid
from query_engine import execute_doctor_search, execute_housing_search
from query_cache import global_query_cache, compile_and_validate_query_with_cache
from database import init_database, get_connection
from safety import validate_sql_sandbox_query, _SQLGLOT_AVAILABLE
from tests.eval_benchmark import run_full_evaluation_benchmark

# Initialize Database
init_database(force_reset=False)

app = FastAPI(
    title="MedData AI & UrbanLocate REST API",
    description="Deterministic Grounded Healthcare & Housing Discovery Engine with AST-Validated SQL Sandboxing (sqlglot) & Bounded LLM Intent Parsing.",
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


# ==============================================================================
# In-Memory Rate Limiter & Benchmark Cache
# NOTE: In-memory stores are scoped to single-process deployments (--workers 1).
# For multi-worker / multi-container horizontal scale, replace with Redis/Memcached.
# ==============================================================================
_RATE_LIMIT_STORE: Dict[str, List[float]] = {}
_LAST_FORCE_REFRESH_PER_IP: Dict[str, float] = {}

# Configurable Trusted Reverse Proxy IPs (Loopback and custom proxy subnets)
TRUSTED_PROXY_IPS = set(
    ip.strip() for ip in os.getenv("TRUSTED_PROXY_IPS", "127.0.0.1,::1,testclient").split(",") if ip.strip()
)

def check_rate_limit(client_ip: str, max_requests: int = 120, window_seconds: int = 60) -> bool:
    """Sliding-window IP rate limiter preventing abuse and DoS."""
    now = time.time()
    if client_ip not in _RATE_LIMIT_STORE:
        _RATE_LIMIT_STORE[client_ip] = []
    
    # Prune timestamps older than window
    timestamps = [t for t in _RATE_LIMIT_STORE[client_ip] if (now - t) < window_seconds]
    if len(timestamps) >= max_requests:
        return False
    timestamps.append(now)
    _RATE_LIMIT_STORE[client_ip] = timestamps
    return True


import logging
import json

logger = logging.getLogger("meddata_api")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

MEDDATA_API_KEY = os.getenv("MEDDATA_API_KEY")
MEDDATA_ALLOW_UNAUTHENTICATED_DEMO = os.getenv("MEDDATA_ALLOW_UNAUTHENTICATED_DEMO", "false").lower() == "true"


def verify_api_key(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")) -> Optional[str]:
    """
    Shared-secret API key verification for protected endpoints.
    - If MEDDATA_API_KEY is configured: enforces matching X-API-Key header (returns 401 on mismatch).
    - If MEDDATA_API_KEY is unset:
        - If MEDDATA_ALLOW_UNAUTHENTICATED_DEMO=true (explicit demo mode): permits request.
        - If MEDDATA_ALLOW_UNAUTHENTICATED_DEMO=false (strict production mode): fails closed with 503 error.
    """
    configured_key = os.getenv("MEDDATA_API_KEY")
    allow_demo = os.getenv("MEDDATA_ALLOW_UNAUTHENTICATED_DEMO", "false").lower() == "true"

    if configured_key:
        if not x_api_key or x_api_key != configured_key:
            raise HTTPException(status_code=401, detail="Unauthorized: Invalid or missing X-API-Key header.")
    elif not allow_demo:
        raise HTTPException(
            status_code=503,
            detail="Service Unavailable: Server requires MEDDATA_API_KEY in production mode. Set MEDDATA_API_KEY or configure MEDDATA_ALLOW_UNAUTHENTICATED_DEMO=true for local demo."
        )
    return x_api_key


# Structured Request ID, Rate Limiting & Timing Middleware
@app.middleware("http")
async def add_request_metadata(request: Request, call_next):
    peer_ip = request.client.host if request.client else "127.0.0.1"
    forwarded = request.headers.get("X-Forwarded-For")

    # Defense-in-depth: Only trust X-Forwarded-For if the immediate connection is from a trusted proxy
    if forwarded and peer_ip in TRUSTED_PROXY_IPS:
        client_ip = forwarded.split(",")[0].strip()
    else:
        client_ip = peer_ip

    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    start_time = time.perf_counter()
    
    # Rate limit check (120 req/min per IP)
    if not check_rate_limit(client_ip, max_requests=120, window_seconds=60):
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.warning(json.dumps({
            "event": "http_request",
            "request_id": request_id,
            "client_ip": client_ip,
            "method": request.method,
            "path": request.url.path,
            "status_code": 429,
            "duration_ms": duration_ms,
            "rate_limited": True
        }))
        return Response(
            content='{"detail":"Rate limit exceeded. Maximum 120 requests per minute."}',
            status_code=429,
            media_type="application/json"
        )

    response: Response = await call_next(request)
    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time-MS"] = str(duration_ms)

    # Structured JSON log (zero PHI or credentials logged)
    logger.info(json.dumps({
        "event": "http_request",
        "request_id": request_id,
        "client_ip": client_ip,
        "method": request.method,
        "path": request.url.path,
        "status_code": response.status_code,
        "duration_ms": duration_ms
    }))

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
        description="'deterministic' (<1ms regex) or 'llm' (Gemini/OpenAI) or 'auto'"
    )
    provider: Optional[str] = Field(
        default="gemini", 
        description="LLM provider ('gemini' or 'openai')"
    )
    use_cache: bool = Field(
        default=True,
        description="Whether to use the in-memory LRU query cache for NL->SQL compilation"
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
    cached: bool = False


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
        "architecture": "Deterministic Grounded Intent Parser with Bounded LLM Fallback & AST SQL Sandbox",
        "endpoints": {
            "query_triage": "POST /api/v1/triage/query",
            "sql_sandbox": "POST /api/v1/sandbox/sql",
            "benchmark_metrics": "GET /api/v1/eval/benchmark",
            "cache_stats": "GET /api/v1/cache/stats",
            "cache_flush": "POST /api/v1/cache/flush",
            "health": "GET /api/v1/health"
        }
    }


@app.get("/api/v1/health", tags=["General"])
def health_check(response: Response):
    """Returns database connectivity, WAL mode status, AST validator status, cache stats, and record counts."""
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
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
        cache_stats = global_query_cache.get_stats()
        return {
            "status": "healthy",
            "database": "SQLite (hospital_ultimate.db)",
            "journal_mode": str(journal_mode).upper(),
            "ast_validator": "sqlglot (active)" if _SQLGLOT_AVAILABLE else "unavailable (fail-closed)",
            "doctors_count": doc_count,
            "properties_count": prop_count,
            "cache_stats": cache_stats,
            "uptime": "100%"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="Database health check failed.")


@app.get("/api/v1/cache/stats", tags=["Cache & Performance"])
def get_cache_statistics():
    """Returns in-memory LRU query cache metrics (hits, misses, hit ratio, TTL, schema hash)."""
    return global_query_cache.get_stats()


@app.post("/api/v1/cache/flush", tags=["Cache & Performance"], dependencies=[Depends(verify_api_key)])
def flush_query_cache():
    """Manually flushes all entries from the in-memory LRU query cache."""
    count = global_query_cache.invalidate_all()
    return {"status": "success", "flushed_entries": count, "message": f"Flushed {count} cache entries."}


@app.post("/api/v1/triage/query", response_model=TriageQueryResponse, tags=["Discovery & Triage"], dependencies=[Depends(verify_api_key)])
def process_triage_query(payload: TriageQueryRequest):
    """
    Executes the Dual-Engine Triage Pipeline with LRU Query Caching & AST Validation:
    1. Checks in-memory LRU query cache for pre-compiled, AST-validated SQL plan.
    2. On miss: parses natural language intent, evaluates safety guardrails, compiles parameterized SQL, and AST validates.
    3. Executes live Parameterized SQL against SQLite ground-truth database to retrieve fresh rows.
    """
    start_time = time.perf_counter()
    
    # Resolve provider API key strictly from server environment variables
    if payload.provider == "openai":
        resolved_api_key = os.getenv("OPENAI_API_KEY")
    else:
        resolved_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")

    # Step 1: Compile & Validate (with Query Cache)
    plan, is_hit, compile_ms = compile_and_validate_query_with_cache(
        prompt=payload.query,
        engine=payload.engine,
        api_key=resolved_api_key,
        provider=payload.provider or "gemini",
        use_cache=payload.use_cache
    )

    # Intercept Safety / Refusal Intents
    if plan.intent in [
        IntentType.EMERGENCY,
        IntentType.MEDICAL_ADVICE,
        IntentType.UNKNOWN_ATTRIBUTE,
        IntentType.PROMPT_INJECTION
    ]:
        lat = round((time.perf_counter() - start_time) * 1000, 2)
        return TriageQueryResponse(
            status="safety_intercepted",
            raw_query=payload.query,
            domain=plan.domain.value,
            intent=plan.intent.value,
            engine_used=f"{payload.engine.title()} Engine",
            ambiguity_detected=False,
            explanation=plan.explanation,
            row_count=0,
            data=[],
            execution_time_ms=lat,
            cached=is_hit
        )

    # Intercept Ambiguity
    if plan.intent == IntentType.AMBIGUOUS:
        lat = round((time.perf_counter() - start_time) * 1000, 2)
        return TriageQueryResponse(
            status="ambiguity_intercepted",
            raw_query=payload.query,
            domain=plan.domain.value,
            intent=plan.intent.value,
            engine_used=f"{payload.engine.title()} Engine",
            ambiguity_detected=True,
            clarification_options=[],
            explanation=plan.explanation,
            row_count=0,
            data=[],
            execution_time_ms=lat,
            cached=is_hit
        )

    # Step 2: Execute Live Database Search (Fresh row fetching)
    rows = []
    if plan.sql_template:
        conn = None
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute(plan.sql_template, plan.params)
            rows = [dict(row) for row in c.fetchall()]
        finally:
            if conn is not None:
                conn.close()

    total_latency = round((time.perf_counter() - start_time) * 1000, 2)

    return TriageQueryResponse(
        status="success",
        raw_query=payload.query,
        domain=plan.domain.value,
        intent=plan.intent.value,
        engine_used=f"{payload.engine.title()} Engine" + (" (Cached)" if is_hit else ""),
        ambiguity_detected=False,
        explanation=plan.explanation,
        sql_executed=plan.sql_template,
        params=plan.params,
        row_count=len(rows),
        data=rows,
        execution_time_ms=total_latency,
        cached=is_hit
    )


@app.post("/api/v1/sandbox/sql", response_model=SQLSandboxResponse, tags=["Security & Sandbox"], dependencies=[Depends(verify_api_key)])
def execute_sql_sandbox(payload: SQLSandboxRequest):
    """
    Validates an ad-hoc SQL query using AST (Abstract Syntax Tree) traversal via SQLGlot:
    - Root Type: Enforces read-only root AST nodes (SELECT, WITH, or recursively validated EXPLAIN).
    - Table Allowlist: Enforces all referenced tables belong to {Doctors, Properties, Appointments, Specialties} or declared CTE aliases.
    - Attack Defense: Blocks mutations (INSERT, UPDATE, DELETE, DROP, ALTER), system catalogs (sqlite_master), and recursive CTEs.
    - Execution Guardrail: Enforces max 100-row cap and instruction step limits (~200,000 SQLite VM instructions) to prevent DoS.
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

    conn = None
    try:
        conn = get_connection()
        conn.row_factory = None
        
        # Guardrail: Prevent runaway CPU execution with progress handler
        # (1000 callbacks × 200 VM instructions ≈ 200,000 SQLite VM instructions)
        step_count = 0
        def step_monitor():
            nonlocal step_count
            step_count += 1
            if step_count > 1000:
                return 1 # Abort runaway query execution
            return 0

        conn.set_progress_handler(step_monitor, 200)

        c = conn.cursor()
        c.execute(payload.sql)
        columns = [desc[0] for desc in c.description] if c.description else []
        # Enforce maximum 100 rows returned from sandbox
        raw_rows = c.fetchmany(100)

        dict_rows = [dict(zip(columns, r)) for r in raw_rows]
        lat = round((time.perf_counter() - start_time) * 1000, 2)

        return SQLSandboxResponse(
            is_safe=True,
            validation_decision="🛡️ SAFE READ-ONLY QUERY (AST & Table Validated)",
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
    finally:
        if conn is not None:
            conn.close()


@app.get("/api/v1/eval/benchmark", tags=["AI & Testing Benchmarks"], dependencies=[Depends(verify_api_key)])
def get_evaluation_benchmark_metrics(
    request: Request,
    engine: str = Query(default="deterministic", description="Engine to evaluate: 'deterministic' or 'llm'"),
    force_refresh: bool = Query(default=False, description="Bypass cache and recompute full 290-query benchmark")
):
    """
    Returns the 290-query reproducible evaluation benchmark metrics.
    Includes in-memory caching (60s TTL) and per-IP force_refresh rate-limiting (5s cooldown) to prevent CPU DoS.
    """
    global _BENCHMARK_CACHE, _LAST_FORCE_REFRESH_PER_IP
    now = time.time()
    client_ip = request.client.host if request.client else "127.0.0.1"

    # Cooldown check for force_refresh
    if force_refresh:
        last_refresh = _LAST_FORCE_REFRESH_PER_IP.get(client_ip, 0.0)
        if (now - last_refresh) < 5.0 and _BENCHMARK_CACHE["data"] is not None:
            return _BENCHMARK_CACHE["data"]
        _LAST_FORCE_REFRESH_PER_IP[client_ip] = now

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
