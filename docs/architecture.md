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
             [ READ-ONLY SQL SECURITY SANDBOX ]
             ├── First-token allowlist (SELECT, WITH, EXPLAIN)
             ├── Table allowlist (Doctors, Properties, Appointments)
             ├── Catalog blocklist (sqlite_master) & DoS caps
             └── Mutation / DDL blocklist
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

### 4. Read-Only SQL Security Sandbox (`safety.py` & `api.py`)
Protects ad-hoc developer SQL execution:
- **Layer 1**: Allows only read-only statements (`SELECT`, `WITH`, `EXPLAIN`).
- **Layer 2**: Enforces table allowlists (`Doctors`, `Properties`, `Appointments`, `Specialties`) while blocking system catalog reads (`sqlite_master`) and recursive CTE DoS vectors.
- **Execution Limits**: Hard cap of 100 returned rows and instruction step limits.
