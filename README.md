# 🏥 MedData AI & UrbanLocate (India)
### Database-Grounded Natural Language Discovery Engine with Dual-Engine Intent Parsing, Parameterized Query Compilation & AST SQL Sandboxing

[![CI & Evaluation Verification](https://github.com/Divyamajm/MedData-Agent/actions/workflows/tests.yml/badge.svg)](https://github.com/Divyamajm/MedData-Agent/actions/workflows/tests.yml)
[![Live Streamlit Demo](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://meddata-divyam.streamlit.app)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![Pytest Passed](https://img.shields.io/badge/pytest-45%20passed-success.svg)](https://pytest.org)

**Architected & Developed by:** [Divyam Sharma](https://github.com/Divyamajm) (*B.Tech CSE, Vellore Institute of Technology, Chennai*)  
**Live Cloud Deployment:** [https://meddata-divyam.streamlit.app/](https://meddata-divyam.streamlit.app/)

---

## 🎯 Architectural Principle: Database-Grounded Query Execution

In high-stakes clinical and real estate discovery, allowing an unconstrained LLM to directly write or execute arbitrary SQL queries against a production database introduces severe hallucination, injection, and schema corruption vulnerabilities.

**MedData AI** implements a **strict separation of concerns**:
1. **Input Boundary**: Natural language queries are parsed into structured filter objects conforming to a strict **Pydantic v2 Schema**.
   - **Dual-Engine Triage**: Supports sub-millisecond deterministic regex/dictionary classification (`<0.2ms` latency) or bounded LLM function calling (**Google Gemini / OpenAI** structured JSON).
2. **Safety & Guardrails Layer**: Programmatically intercepts acute emergencies (triggering 112/911 redirection), blocks clinical diagnosis/prescription attempts, identifies untracked schema attributes (zero guessing), and filters prompt injections.
3. **Deterministic Query Compiler**: Converts validated Pydantic models into parameterized SQL queries with strict column allowlists (`ALLOWED_DOCTOR_COLUMNS`, `ALLOWED_SORT_METRICS`). **The LLM never touches, writes, or executes SQL.**
4. **2-Layer AST SQL Sandbox**: Sandboxed query execution engine with first-token allowlists (`SELECT`, `WITH`, `EXPLAIN`) and DDL/mutation blocklists (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `PRAGMA`).

```
                              ┌────────────────────────────────────────┐
                              │     User Natural Language Query        │
                              └──────────────────┬─────────────────────┘
                                                 │
                                                 ▼
                              ┌────────────────────────────────────────┐
                              │        DUAL-ENGINE INTENT PARSER       │
                              │  ┌──────────────────┐ ┌──────────────┐ │
                              │  │ Deterministic AST│ │ Bounded LLM  │ │
                              │  │  Regex (<0.2ms)  │ │ (Structured) │ │
                              │  └──────────────────┘ └──────────────┘ │
                              └──────────────────┬─────────────────────┘
                                                 │
                                                 ▼
                              ┌────────────────────────────────────────┐
                              │       MULTI-TIER SAFETY LAYER          │
                              │  • Acute Emergency Protocol (112/911)  │
                              │  • Medical Advice / Diagnosis Refusal  │
                              │  • Unknown Field Zero-Guessing Filter  │
                              │  • Prompt Injection Defense            │
                              └──────────────────┬─────────────────────┘
                                                 │
                                                 ▼
                              ┌────────────────────────────────────────┐
                              │      PYDANTIC v2 SCHEMA VALIDATION     │
                              │     (SearchFilters / HousingFilters)   │
                              └──────────────────┬─────────────────────┘
                                                 │
                                                 ▼
                              ┌────────────────────────────────────────┐
                              │     PARAMETERIZED SQL QUERY BUILDER    │
                              │  (Explicit Column Whitelists & Index)  │
                              └──────────────────┬─────────────────────┘
                                                 │
                                                 ▼
                              ┌────────────────────────────────────────┐
                              │     SQLite / PostgreSQL DATA LAKE      │
                              │  (200 Indian Doctors & 50 Properties)  │
                              └──────────────────┬─────────────────────┘
                                                 │
                                                 ▼
                              ┌────────────────────────────────────────┐
                              │   Explainable Results + Audit Trail    │
                              │   (Interactive Cards, Map, PDF Report) │
                              └────────────────────────────────────────┘
```

---

## 📊 Scientific Evaluation Benchmark (290 Labeled Queries)

The repository includes an empirical scientific evaluation suite (`python -m tests.eval_benchmark`) measuring precision, recall, accuracy, and latency distributions across **290 multi-domain queries**:

| Metric | Measured Score | Evaluation Focus |
|---|:---:|---|
| **Intent Classification Accuracy** | **84.8%** | Multi-class intent routing across 14 distinct intent categories. |
| **Entity Extraction Precision** | **93.1%** | Specialty, fee thresholds, city names, and distance radius matching. |
| **Clinical Safety Refusal Precision** | **96.3%** | Intercepting medical diagnosis, medication questions, and emergency symptoms without false positives. |
| **Clinical Safety Refusal Recall** | **82.1%** | Proportion of dangerous queries successfully caught and redirected. |
| **Ambiguity Interception Rate** | **98.3%** | Intercepting subjective queries (*"best doctor"*, *"top hospital"*) for metric clarification. |
| **SQL Execution & Grounding Rate** | **100.0%** | Zero SQL syntax errors, 100% database grounding with no fabricated rows. |
| **Deterministic Pipeline Latency** | **0.15 ms** | Mean execution latency of deterministic AST compiler (`p50: 0.12ms`, `p95: 0.34ms`, `p99: 0.69ms`). |

---

## 🚀 Key Platform Features

1. **🏥 Indian Super-Specialty Clinical Discovery**:
   - 200 real verified Indian medical specialists across 10 specialties (Cardiology, Neurology, Orthopedics, Pediatrics, Oncology, ENT, Gynecology, Dermatology, Psychiatry, General Medicine) in top hospitals (Apollo, Fortis, Max, Manipal, AIIMS).
2. **🏠 UrbanLocate Real Estate Discovery**:
   - 50 curated residential properties across 5 Indian Metros (Bengaluru, Mumbai, Delhi-NCR, Chennai, Hyderabad) with crime safety indexes, school ratings, and transit proximity.
3. **📂 Dynamic CSV Auto-Analyzer**:
   - Zero-shot dataset ingestion: Upload any arbitrary CSV spreadsheet to automatically profile data types, calculate statistical distributions, and execute natural language filtering.
4. **🎙️ Native Web Speech API Voice Dictation**:
   - Browser-native speech-to-text with Indian English (`en-IN`) acoustic models and auto-query execution.
5. **📄 1-Click Executive PDF / HTML Brief Export**:
   - Generates clean, printable A4 clinical reports with anti-hallucination timestamps and query execution watermarks.
6. **🔒 AST-Validated SQL Security Sandbox**:
   - Interactive SQL editor allowing safe ad-hoc querying while blocking all mutation and DDL injection attempts.
7. **📅 Conflict-Free Appointment Booking**:
   - Relational appointment scheduling with double-booking collision prevention and RFC 5545 `.ics` Apple/Google Calendar export.

---

## 🌐 Production REST API Service Layer (`FastAPI`)

The platform includes a dedicated **FastAPI REST API** (`api.py`) exposing the triage and SQL sandbox engine with interactive OpenAPI Swagger documentation at `/docs`.

### Starting the REST API Server:
```bash
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

### API Endpoints:
- `POST /api/v1/triage/query`: Natural language triage and structured search.
- `POST /api/v1/sandbox/sql`: 2-layer AST validated read-only SQL execution.
- `GET /api/v1/eval/benchmark`: Live scientific evaluation benchmark execution.
- `GET /api/v1/health`: Health status and database row statistics.

---

## 🧪 Comprehensive Automated Testing & Benchmarks

The project provides three testing and evaluation suites:

```bash
# 1. Run standard Pytest across all test suites (45/45 Passed in ~1.0s):
pytest -v

# 2. Run Core 32-Case Verification Suite & SQL Sandbox Tests (100% Pass):
python -m tests.test_suite

# 3. Run the 290-Query Scientific AI Evaluation Benchmark:
python -m tests.eval_benchmark
```

---

## 📚 Technical Documentation & System Specifications
- **[Architecture Specification](docs/architecture.md)**: Deep dive into the Grounding Layer, IntentRouter, SafetyGate, and QueryCompiler.
- **[Security & Threat Model](docs/security_and_threat_model.md)**: AST SQL sandbox rules, prompt injection defense, and emergency routing.
- **[Evaluation Methodology](docs/evaluation_methodology.md)**: Benchmark dataset composition (290 queries) and statistical metrics.
- **[Design Decisions & Tradeoffs](docs/design_decisions.md)**: Why bounded LLMs, deterministic fallbacks, and Pydantic v2 schemas.

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
