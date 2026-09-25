# 🏥 MedData AI & UrbanLocate (India)
### Database-Grounded Natural Language Discovery Engine with Dual-Engine Intent Parsing, Parameterized Query Compilation & AST-Parsed SQL Sandboxing

[![CI & Evaluation Verification](https://github.com/Divyamajm/MedData-Agent/actions/workflows/tests.yml/badge.svg)](https://github.com/Divyamajm/MedData-Agent/actions/workflows/tests.yml)
[![Live Streamlit Demo](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://meddata-divyam.streamlit.app)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![Docker Ready](https://img.shields.io/badge/Docker-Containerized-2496ED.svg?logo=docker)](Dockerfile)
[![Pytest Passed](https://img.shields.io/badge/pytest-146%20passed-success.svg)](https://pytest.org)

**Architected & Developed by:** [Divyam Sharma](https://github.com/Divyamajm) (*B.Tech CSE, Vellore Institute of Technology, Chennai*)  
**Live Cloud Deployment:** [https://meddata-divyam.streamlit.app/](https://meddata-divyam.streamlit.app/)

---

## 🎯 Architectural Principle: Database-Grounded Query Execution

In high-stakes clinical and real estate discovery, allowing an unconstrained LLM to directly write or execute arbitrary SQL queries against a production database introduces severe hallucination, injection, and schema corruption vulnerabilities.

**MedData AI** implements a **strict separation of concerns**:
1. **Input Boundary**: Natural language queries are parsed into structured filter objects conforming to a strict **Pydantic v2 Schema**.
   - **Dual-Engine Triage**: Supports sub-millisecond deterministic regex/dictionary classification (`<0.2ms` compilation latency) or bounded LLM function calling (**Google Gemini / OpenAI** structured JSON).
2. **Safety & Guardrails Layer**: Programmatically intercepts acute emergencies (triggering India's **112** National Emergency Protocol), blocks clinical diagnosis/prescription attempts, identifies untracked schema attributes (zero guessing), and filters prompt injections.
3. **Query Caching & Invalidation Layer**: In-memory thread-safe LRU query plan cache that memoizes the expensive NL-to-SQL translation and AST validation step while keeping raw database row execution live and fresh.
4. **Deterministic Query Compiler**: Converts validated Pydantic models into parameterized SQL queries with strict column allowlists (`ALLOWED_DOCTOR_COLUMNS`, `ALLOWED_SORT_METRICS`). **The LLM never touches, writes, or executes SQL.**
5. **AST-Parsed SQL Security Sandbox (`sqlglot`)**: Real Abstract Syntax Tree (AST) query validation walking all `exp.Table` nodes to enforce table allowlists (`Doctors`, `Appointments`, `Specialties`) across CTEs, subqueries, and comma joins, while blocking internal system catalogs (`sqlite_master`) and execution DoS attacks.

```
                              ┌────────────────────────────────────────┐
                              │     User Natural Language Query        │
                              └──────────────────┬─────────────────────┘
                                                 │
                                                 ▼
                              ┌────────────────────────────────────────┐
                              │       MULTI-TIER SAFETY LAYER          │
                              │  • Acute Emergency Protocol (112)      │  ──► [BYPASS CACHE]
                              │  • Medical Advice / Diagnosis Refusal  │
                              │  • Unknown Field Zero-Guessing Filter  │
                              │  • Prompt Injection Defense            │
                              └──────────────────┬─────────────────────┘
                                                 │
                                                 ▼
                              ┌────────────────────────────────────────┐
                              │      NORMALIZED QUERY CACHE (LRU)      │
                              │    (Trimmed / Lowercase / Collapsed)   │
                              │  ┌───────────────┐  ┌────────────────┐ │
                              │  │  TTL Expiry   │  │  Schema Drift  │ │
                              │  │ (10 min TTL)  │  │ (SHA-256 Check)│ │
                              │  └───────────────┘  └────────────────┘ │
                              └──────────────────┬─────────────────────┘
                                      │                  │
                           [CACHE HIT]│                  │[CACHE MISS]
                                      ▼                  ▼
                       ┌──────────────────────┐   ┌────────────────────────────┐
                       │ Return Validated SQL │   │ DUAL-ENGINE INTENT PARSER  │
                       │     & Parameter Spec │   │ (Rule / Structured LLM)    │
                       └──────────────┬───────┘   └──────────────┬─────────────┘
                                      │                          │
                                      │                          ▼
                                      │           ┌────────────────────────────┐
                                      │           │ PYDANTIC v2 SCHEMA FILTER  │
                                      │           └──────────────┬─────────────┘
                                      │                          │
                                      │                          ▼
                                      │           ┌────────────────────────────┐
                                      │           │ PARAMETERIZED SQL COMPILER │
                                      │           └──────────────┬─────────────┘
                                      │                          │
                                      │                          ▼
                                      │           ┌────────────────────────────┐
                                      │           │ AST SQL VALIDATION SANDBOX │
                                      │           └──────────────┬─────────────┘
                                      │                          │
                                      └──────────────────────────┼─────────────┐
                                                                 │ Store Plan  │
                                                                 ▼             ▼
                                                  ┌────────────────────────────┐
                                                  │    LIVE SQLITE DATABASE    │
                                                  │ (Fresh Table Row Fetching) │
                                                  └──────────────┬─────────────┘
                                                                 │
                                                                 ▼
                                                  ┌────────────────────────────┐
                                                  │ Explainable Results & Card │
                                                  └────────────────────────────┘
```

---

## ⚡ Query Caching & Dual Invalidation Architecture

### Why Caching Was Added
In conversational discovery pipelines, repeated or semantically equivalent natural language queries (*"cardiologist in chennai under 1500"*, *"  Cardiologist   in Chennai  under 1500 "*), pagination requests, and concurrent user filtering frequently re-trigger the entire computational chain: **Intent Classification → Multi-Tier Safety Gates → Pydantic Schema Parsing → Query Parameter Generation → AST Traversal Sandboxing**.

Re-evaluating AST validation and intent extraction on identical NL prompts wastes CPU cycles and adds unnecessary latency.

**Key Architecture Decision:** The cache **only stores the compiled and AST-validated SQL query plan and parameter bindings**, NOT the raw query result rows. This ensures that database reads always fetch live, real-time records from SQLite (such as newly scheduled appointments or updated fee structures) while eliminating repeated query compilation overhead.

### Invalidation Strategy (TTL + Schema-Hash Verification)
Caching SQL generation without strict invalidation introduces severe correctness and security risks. MedData implements a **dual invalidation strategy**:

1. **TTL-Based Expiry (Time-to-Live = 10 Minutes):**
   - Each cached plan records an epoch timestamp `cached_at`.
   - On lookup, if `(current_time - cached_at) > 600s`, the entry is tagged as `[CACHE EXPIRY]`, evicted, and recompiled fresh.
2. **Schema-Drift Invalidation (SHA-256 Schema Hashing):**
   - On database initialization and periodic checks, the system computes a SHA-256 fingerprint of the SQLite catalog (`SELECT type, name, tbl_name, sql FROM sqlite_master ORDER BY type, name`).
   - If a table is altered, added, or dropped (e.g. migration or DDL mutation), the schema hash changes.
   - The cache detects the mismatch, logs `[CACHE SCHEMA-INVALIDATION]`, and flushes all stale query plans to guarantee that obsolete column/table references are never reused.

**Why Both Are Necessary:**
- **TTL Alone is Insufficient:** If a database migration adds or removes columns at minute 2 of a 10-minute window, TTL-only caching would serve invalid or broken SQL for the remaining 8 minutes.
- **Schema Hashing Alone is Insufficient:** Schema structure can remain static while semantic intent mappings, dictionary definitions, or safety bounds evolve. TTL guarantees bounded cache staleness.

### Architectural Trade-offs & Safety Bypass
- **Memory Overhead vs. Latency:** In-memory LRU storage (`collections.OrderedDict` with `max_size=100`) bounds memory footprint while achieving sub-0.05ms lookup times.
- **Strict Emergency Triage Bypass (Non-Negotiable Invariant):** Acute emergency prompts (*"severe chest pain and shortness of breath"*, *"sudden slurred speech"*) are **never cached**. Emergency triage guardrails execute fresh on every request to prevent stale emergency routing.

### Measured Empirical Benchmark Results
Benchmarked on 18 representative clinical discovery queries (10 unique initial queries + 8 repeated/near-duplicate queries) using `python benchmark.py`:

| Execution Mode | Total Pipeline Time (18 Queries) | Avg Latency on Repeated Queries | Cache Hit Rate |
|---|:---:|:---:|:---:|
| **Caching Disabled (Baseline)** | **28.344 ms** | **0.573 ms / query** | 0.0% (0/7) |
| **Caching Enabled (LRU + Invalidation)** | **11.246 ms** | **0.110 ms / query** | **100.0% (7/7)** |
| **Measured Improvement** | **-60.3% Total Time** | **-80.8% Latency (~5.2x speedup)** | **Sub-0.1ms Hits** |

*To reproduce these numbers locally, run `python benchmark.py`.*

---

## 📊 Empirical Evaluation Benchmark (290 Labeled Queries)

The repository includes a comprehensive, reproducible labeled evaluation suite (`python -m tests.eval_benchmark`) measuring precision, recall, accuracy, and latency distributions across **290 multi-domain test queries**:

| Metric | Measured Score | Evaluation Focus |
|---|:---:|---|
| **Intent Classification Accuracy** | **87.2%** | Multi-class intent routing across 14 distinct intent categories on labeled set. |
| **Entity Extraction Precision** | **93.1%** | Specialty, fee boundaries, city names, and distance radius matching. |
| **Clinical Safety Refusal Precision** | **96.6%** | Intercepting medical diagnosis, medication questions, and emergency symptoms without false positives. |
| **Clinical Safety Refusal Recall** | **89.5%** | Proportion of dangerous queries successfully caught and redirected. |
| **Ambiguity Interception Rate** | **98.3%** | Intercepting subjective queries (*"best doctor"*, *"top hospital"*) for metric clarification. |
| **SQL Execution & Grounding Rate** | **100.0%** | Zero SQL syntax errors, 100% database grounding with no fabricated rows. |
| **Deterministic Pipeline Latency** | **~0.20 ms** | Mean execution latency of deterministic compiler on local RAM (`p50: 0.17ms`, `p95: 0.49ms`, `p99: 2.02ms`). *(Excludes external cloud LLM API network roundtrips)*. |

*Note: Benchmark metrics are generated dynamically and reproducible locally via `python -m tests.eval_benchmark`.*

---

## 🚀 Key Platform Features

1. **🏥 Indian Super-Specialty Clinical Discovery**:
   - 200 procedurally generated synthetic specialist records modeled on Indian healthcare directory schemas across 5 core super-specialties (Cardiology, Neurology, Orthopedics, Pediatrics, Emergency) in top hospital networks (Apollo, Fortis, Max, Manipal, AIIMS).
2. **🏠 UrbanLocate Real Estate Discovery**:
   - 50 procedurally generated synthetic residential property records across 5 Indian Metros (Bengaluru, Mumbai, Delhi-NCR, Chennai, Hyderabad) with crime safety indexes, school ratings, and transit proximity.
3. **📂 Dynamic CSV Auto-Analyzer**:
   - Zero-shot dataset ingestion: Upload any arbitrary CSV spreadsheet to automatically profile data types, calculate statistical distributions, and execute natural language filtering.
4. **🎙️ Native Web Speech API Voice Dictation**:
   - Browser-native speech-to-text with Indian English (`en-IN`) acoustic models and auto-query execution.
5. **📄 1-Click Executive PDF / HTML Brief Export**:
   - Generates clean, printable A4 clinical reports with anti-hallucination timestamps and query execution watermarks.
6. **🔒 AST-Parsed SQL Security Sandbox**:
   - Interactive SQL editor powered by `sqlglot` AST traversal, enforcing table allowlists across CTEs, subqueries, and joins while blocking mutation/DDL attacks.
7. **📅 Conflict-Free Appointment Booking**:
   - Relational appointment scheduling with double-booking collision prevention and RFC 5545 `.ics` Apple/Google Calendar export.

---

## 🌐 Production REST API Service Layer (`FastAPI`)

The platform includes a dedicated **FastAPI REST API** (`api.py`) exposing the triage and SQL sandbox engine with interactive OpenAPI Swagger documentation at `/docs`.

### Starting the REST API Server:
```bash
python -m uvicorn api:app --host 0.0.0.0 --port 8000 --workers 1
```

### API Endpoints:
- `POST /api/v1/triage/query`: Natural language triage and structured search. Server-side provider keys (`GEMINI_API_KEY`, `OPENAI_API_KEY`) are resolved securely on the host. Protected by fail-closed `X-API-Key` auth & sliding-window rate limiting.
- `POST /api/v1/sandbox/sql`: AST-validated read-only SQL execution (`sqlglot`) with table allowlisting, EXPLAIN mutation defense, fail-closed enforcement, and DoS caps.
- `GET /api/v1/eval/benchmark`: Cached 290-query reproducible evaluation benchmark metrics (60s TTL, 5s per-IP cooldown).
- `GET /api/v1/health`: Health status, WAL journal mode status, AST validator status (`sqlglot`), and database row statistics.

---

## 🐳 Docker Containerized Deployment

Run both the Streamlit frontend (`:8501`) and FastAPI backend (`:8000`) simultaneously via Docker Compose:

```bash
docker compose up --build
```

---

## 🧪 Comprehensive Automated Testing & Benchmarks

The project provides five testing and evaluation suites:

```bash
# 1. Run standard Pytest across all test suites (146/146 Passed):
python -m pytest -v

# 2. Run Core 32-Case Verification Suite, 26 SQL Sandbox & 6 Query Cache Tests (100% Pass):
python -m tests.test_suite

# 3. Run the LRU Query Cache Benchmark (Reproducible Latency & Hit Rate Metrics):
python benchmark.py

# 4. Run the 290-Query Reproducible AI Evaluation Benchmark:
python -m tests.eval_benchmark

# 5. Run the In-Process Concurrency Load Benchmark (10, 50, 100 workers):
# (Measures in-process in-memory ASGI dispatch throughput across thread pools)
python -m tests.load_test
```

---

## 📚 Technical Documentation & System Specifications
- **[Verification Run Log](docs/verification_run.md)**: Full, timestamped CLI output of all 4 test suites (Pytest, Standalone Suite, 290-Query Benchmark, Load Test).
- **[Architecture Specification](docs/architecture.md)**: Deep dive into the Grounding Layer, IntentRouter, SafetyGate, and QueryCompiler.
- **[Security & Threat Model](docs/security_and_threat_model.md)**: SQL sandbox AST table allowlist rules, prompt injection defense, trusted proxy headers, and fail-closed auth.
- **[Evaluation Methodology](docs/evaluation_methodology.md)**: Benchmark dataset composition (290 queries) and statistical metrics.
- **[Design Decisions & Tradeoffs](docs/design_decisions.md)**: Why bounded LLMs, deterministic fallbacks, Pydantic v2 schemas, and single-worker in-memory rate limiting.

---

## 💻 Local Development & Installation

### 1. Clone the Repository:
```bash
git clone https://github.com/Divyamajm/MedData-Agent.git
cd MedData-Agent
```

### 2. Install Dependencies:
```bash
pip install -r requirements.txt
```

### 3. Run the Streamlit Application:
```bash
streamlit run app.py
```

---

## 📄 License
This project is open-source and licensed under the [MIT License](LICENSE).
