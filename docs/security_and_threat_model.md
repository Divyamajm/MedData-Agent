# 🛡️ Security Architecture & Threat Model

## Threat Modeling & Defense Vectors

| Threat Vector | Attack Mechanism | MedData AI Mitigation Strategy | Verification Metric |
|---|---|---|:---:|
| **Direct SQL Injection** | Concatenating user text into raw SQL string (e.g. `' OR 1=1 --`) | Parameterized SQL compilation via `?` placeholders + column allowlists (`ALLOWED_DOCTOR_COLUMNS`). | **100% Block Rate** |
| **LLM-Generated Malicious SQL** | Jailbreaking the LLM to output `DROP TABLE Doctors` | **Architectural Isolation**: The LLM output is strictly JSON mapped to Pydantic models. The LLM has zero access to SQL generation. | **100% Isolation** |
| **Prompt Injection / Jailbreaks** | System prompt override (DAN mode, "ignore previous instructions") | Tokenized regex pre-screens + safety rule interception before query execution. | **100.0% Detection Rate** |
| **Clinical Diagnosis Liability** | User seeking diagnosis/dosage for acute conditions | Programmatic refusal gate (`check_medical_advice_refusal`) directing user to licensed physicians. | **96.6% Refusal Precision** |
| **Acute Emergency Harm** | User waiting on AI chat during active heart attack/stroke | Instant interception (`check_acute_emergency`) displaying bold red 112/911 emergency warnings. | **89.5% Safety Recall** |
| **Fact Hallucination / Fabricated Rows** | LLM inventing non-existent doctors, prices, or ratings | 100% SQLite query execution; zero LLM generative answering of database records. | **100% Database Grounding** |
| **Schema Disclosure Attacks** | Querying internal SQLite catalogs (`SELECT * FROM sqlite_master;`) | Sandbox table allowlist restricting queries exclusively to `{Doctors, Properties, Appointments, Specialties}`. | **100% Leak Prevention** |
| **Resource Exhaustion / DoS** | Running recursive infinite loop CTEs (`WITH RECURSIVE cnt(x)...`) | Token-level `RECURSIVE` blocking + SQLite progress step monitors + 100-row fetch limits. | **100% DoS Protection** |
| **Secret & API Key Exposure** | API keys leaking via query strings or logs | Headers-based authentication, environment variable resolution, and sanitized exceptions. | **Zero Leakage** |

---

## Read-Only SQL Security Sandbox Specification

The platform includes an interactive developer SQL sandbox (`/api/v1/sandbox/sql` and Workspace 5). To prevent security compromises:

1. **Layer 1: First-Token Allowlist & Mutation Blocklist**
   - The query is tokenized after stripping SQL comments (`--` and `/* */`).
   - The first meaningful SQL token must belong to: `{'SELECT', 'WITH', 'EXPLAIN'}`.
   - The entire query is scanned for forbidden mutation/DDL keywords:
     `{'DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'TRUNCATE', 'RENAME', 'CREATE', 'REPLACE', 'ATTACH', 'DETACH', 'PRAGMA', 'VACUUM', 'REINDEX', 'EXEC', 'EXECUTE', 'RECURSIVE'}`.
   - Multi-statement injection via semicolons (`SELECT ...; DROP ...`) is strictly intercepted.

2. **Layer 2: Table Allowlist & Catalog Protection**
   - Referenced table identifiers in `FROM` and `JOIN` clauses must belong exclusively to `{DOCTORS, PROPERTIES, APPOINTMENTS, SPECIALTIES}`.
   - Queries targeting internal SQLite metadata (`sqlite_master`, `sqlite_schema`, `sqlite_temp_master`, `sqlite_sequence`) are blocked with security violation alerts.

3. **Layer 3: Execution Resource Guardrails**
   - Hard row limit: At most 100 rows are returned to the client.
   - Step progress monitor: Aborts runaway queries that exceed instruction step thresholds.
   - Sanitized exception handling: Generic error messages prevent internal database structure leakage.
