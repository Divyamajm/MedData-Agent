# 🏛️ Architecture & System Design Specification

## Overview
**MedData AI** is a database-grounded natural-language discovery and clinical triage platform. The primary architectural invariant is:

> **The LLM (Language Model) is strictly bounded to natural-language intent parsing at the ingress boundary. The LLM NEVER generates, sees, or executes SQL queries against the database.**

---

## High-Level Architecture Diagram

```
                 USER / CLIENT
                       │
       ┌───────────────┴───────────────┐
       ▼                               ▼
  Streamlit UI                    FastAPI REST API
  (Port 8501)                     (Port 8000 /docs)
       │                               │
       └───────────────┬───────────────┘
                       │
                       ▼
            [ MULTI-TIER SAFETY GATE ]
            ├── Acute Emergency Check (911/112)
            ├── Clinical Medical Advice Refusal
            ├── Unknown Attribute Filter (Zero-Guessing)
            └── Prompt Injection Pre-Screen
                       │
                       ▼
           [ DUAL-ENGINE INTENT ROUTER ]
          ┌────────────────┴────────────────┐
          ▼                                 ▼
   Deterministic Rule                 Bounded LLM
      Regex Engine                 Structured Parser
   (Latency < 0.2ms)               (Gemini / OpenAI)
          │                                 │
          └────────────────┬────────────────┘
                           │
                           ▼
             [ PYDANTIC v2 SCHEMA VALIDATOR ]
             ├── Type enforcement
             ├── Canonical specialty normalization
             └── Constraint boundary checks
                           │
                           ▼
             [ PARAMETERIZED QUERY COMPILER ]
             ├── Allowlist column validation
             ├── SQL placeholder binding (? / :val)
             └── Zero string-concatenation guarantee
                            │
                            ▼
              [ AST-PARSED SQL SECURITY SANDBOX ]
              ├── Root AST type allowlist (SELECT, WITH, validated EXPLAIN)
              ├── Full-tree table allowlist (Doctors, Properties, Appointments, Specialties)
              ├── Catalog blocklist (sqlite_master) & Recursive CTE DoS blocks
              ├── Fail-Closed Dependency Enforcement (sqlglot required)
              └── Instruction step monitor (200k VM steps) & 100-row cap
                            │
                            ▼
              [ SQLITE / DATA LAKE STORAGE ]
              ├── 200 Synthetic Indian Specialist Records (WAL Mode)
              ├── 50 Synthetic UrbanLocate Property Records
              └── Real-Time ACID Appointments
                            │
                            ▼
              [ EXPLAINABILITY & AUDIT TRAIL ]
              └── Execution metadata, Latency, Grounding proofs
```

---

## Architectural Components

### 1. Multi-Tier Safety Gate (`safety.py`)
Intercepts queries before any parsing or database execution occurs:
- **Acute Emergency Protocol**: Detects active life-threatening symptoms (chest pain, stroke, uncontrolled bleeding) and returns immediate emergency routing (112 / 911).
- **Clinical Medical Advice Refusal**: Refuses clinical diagnosis, medication prescriptions, and drug dosage calculations.
- **Unknown Attribute Filter**: Protects database factuality by refusing queries requesting untracked attributes (e.g. spoken languages, surgical volume counts).
- **Prompt Injection Defense**: Intercepts jailbreak prompts, system-prompt extraction attempts, and raw SQL injection keywords.

### 2. Dual-Engine Intent Router (`intent_parser.py` & `llm_parser.py`)
- **Deterministic Rule Engine**: Sub-millisecond rule-based parser utilizing regex pattern extractors and specialty synonym dictionaries (`~0.15ms` local RAM latency).
- **Bounded LLM Engine**: Employs Google Gemini (`gemini-2.0-flash`) or OpenAI with structured JSON Schema output mode.

### 3. Parameterized Query Compiler (`query_engine.py`)
Converts validated `SearchFilters` into secure parameterized SQL:
- Uses strictly allowlisted column sets (`ALLOWED_DOCTOR_COLUMNS`, `ALLOWED_SORT_METRICS`).
- Values are bound through SQLite parameter placeholders (`?`), preventing SQL injections.

### 4. AST-Parsed SQL Security Sandbox (`safety.py` & `api.py`)
Protects ad-hoc developer SQL execution using real AST syntax tree traversal via `sqlglot`:
- **Fail-Closed Security**: If `sqlglot` is missing or fails to import, the sandbox refuses execution unconditionally rather than degrading to a weaker validator.
- **AST Root & Statement Traversal**: Allows only read-only statements (`SELECT`, `WITH`, or recursively validated `EXPLAIN`). Blocks mutations (`DROP`, `DELETE`, `INSERT`, `UPDATE`, `ALTER`).
- **Table Allowlist**: Walks all `exp.Table` nodes across `FROM`, explicit `JOIN`, comma joins, subqueries, and CTE bodies to ensure only allowed tables (`Doctors`, `Properties`, `Appointments`, `Specialties`) or declared CTE aliases are referenced.
- **Execution Limits & Teardown**: Hard cap of 100 returned rows, SQLite progress handler capping VM instructions at ~200,000 steps, and guaranteed `try ... finally: conn.close()` connection teardown.
