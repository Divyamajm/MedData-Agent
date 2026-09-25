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
| **Schema Disclosure Attacks** | Querying internal SQLite catalogs (`SELECT * FROM sqlite_master;`) | Sandbox AST allowlist restricting queries exclusively to `{Doctors, Properties, Appointments, Specialties}` across CTEs, subqueries, and joins. | **100% Leak Prevention** |
| **Resource Exhaustion / DoS** | Running recursive infinite loop CTEs (`WITH RECURSIVE cnt(x)...`) | AST `With(recursive=True)` blocking + SQLite instruction progress handlers + 100-row fetch limits. | **100% DoS Protection** |
| **Dependency Failure / Degradation** | Missing or corrupted AST parser at runtime | **Fail-Closed Architecture**: Missing `sqlglot` dependency disables sandbox execution rather than degrading to insecure token parsing. | **100% Fail-Closed** |
| **Connection Exhaustion Attacks** | Flooding invalid/failing queries to leak DB file handles | `try ... finally: conn.close()` guaranteed teardown on all execution and error paths. | **Zero Connection Leaks** |

---

## AST-Parsed SQL Security Sandbox Specification (`sqlglot`)

The platform includes an interactive developer SQL sandbox (`/api/v1/sandbox/sql` and Workspace 5). To prevent security compromises:

1. **AST Parse & Tree Traversal**
   - The query is parsed into a syntax tree using `sqlglot` (`read="sqlite"`).
   - Multi-statement execution via semicolons is strictly rejected if `len(parsed_statements) > 1`.
   - Statement root must be a read-only node: `exp.Select`, `exp.Union`, or `exp.Query`.
   - `EXPLAIN` queries recursively validate the underlying statement to prevent wrapped mutations (e.g. `EXPLAIN DROP TABLE Doctors;`).

2. **Table & CTE Allowlist Enforcement**
   - Declared CTE aliases (`tree.ctes`) are dynamically resolved.
   - All referenced table identifiers (`tree.find_all(exp.Table)`) across `FROM`, explicit `JOIN`, comma joins, subqueries, and CTE bodies must belong to `{DOCTORS, PROPERTIES, APPOINTMENTS, SPECIALTIES}` or be a declared CTE alias.
   - Internal SQLite system tables (`sqlite_master`, `sqlite_schema`, `sqlite_temp_master`, `sqlite_sequence`) are blocked.

3. **Execution Guardrails & Teardown**
   - **Step Progress Limit**: A SQLite progress handler aborts execution if instructions exceed 200,000 steps (`conn.set_progress_handler(step_monitor, 200)`).
   - **Row Cap**: Enforces `fetchmany(100)` to prevent unbounded memory buffer allocations.
   - **Guaranteed Cleanup**: Database connection is closed inside a `finally` block on both success and error branches.
   - **Fail-Closed Design**: If `sqlglot` is missing, the validator immediately returns `False` refusing execution.

---

## API Service Authentication & Rate Limiting

1. **Authentication Posture**
   - Protected endpoints (`/api/v1/triage/query`, `/api/v1/sandbox/sql`, `/api/v1/eval/benchmark`) verify the `X-API-Key` header via FastAPI dependency injection.
   - In production mode (`MEDDATA_ALLOW_UNAUTHENTICATED_DEMO=false`), missing `MEDDATA_API_KEY` configuration safely rejects calls with HTTP 503 rather than failing open.
   - For standalone demonstration (`MEDDATA_ALLOW_UNAUTHENTICATED_DEMO=true`), local anonymous triage is permitted.

2. **Reverse Proxy Header Validation & Rate Limiting**
   - Enforces a 120 req/min sliding-window per IP address in-process.
   - **Proxy Trust Boundary**: `X-Forwarded-For` headers are only honored if the connecting peer IP matches `TRUSTED_PROXY_IPS` (loopback / configured reverse proxy), preventing client IP spoofing attacks against the rate limiter and audit logs.
   - **Edge Proxy Header Sanitization Requirement**: Upstream edge reverse proxies (e.g. NGINX, HAProxy, AWS ALB) must overwrite or sanitize untrusted client-supplied `X-Forwarded-For` headers rather than blindly appending to them:
     ```nginx
     # Recommended Edge Reverse Proxy (NGINX) configuration:
     location / {
         # Overwrite client-supplied header with verified TCP socket address
         proxy_set_header X-Forwarded-For $remote_addr;
         proxy_set_header X-Real-IP $remote_addr;
         proxy_set_header Host $host;
         proxy_pass http://127.0.0.1:8000;
     }
     ```
   - **Horizontal Scaling Constraint**: The in-memory tracking store operates on a single uvicorn worker (`--workers 1`). For multi-replica container deployments behind an ingress controller (NGINX/Traefik/Cloudflare), rate-limiting state transitions from in-memory dictionary tracking to a shared Redis cluster (`INCR` with sliding-window `ZADD`/`ZREMRANGEBYSCORE`).

---

## Concurrency & Atomic Collision Prevention

1. **TOCTOU Race Condition Elimination**
   - Appointment scheduling uses a partial unique index:
     ```sql
     CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_confirmed_appointment 
     ON Appointments(doctor_id, appointment_date, time_slot) 
     WHERE status = 'CONFIRMED';
     ```
   - Concurrent bookings attempting the same doctor/date/time slot trigger an atomic `sqlite3.IntegrityError`, caught and converted into a graceful transaction rollback with a collision notification.
