# 💡 Architectural Design Decisions & Tradeoff Analysis

## 1. Why Bounded LLM vs Pure Text-to-SQL (Vanna/LangChain style)?
- **Problem**: Letting an LLM directly generate SQL strings leads to hallucinated column names, invalid joins, and critical SQL injection vulnerabilities.
- **Decision**: The LLM is restricted to outputting JSON matching our typed Pydantic schema (`SearchFilters`).
- **Benefit**: Parameterized SQL is generated 100% deterministically by `query_engine.py`. Even if the LLM output is adversarial, the compiler only uses parameterized placeholders (`?`) and allowlisted column names.

---

## 2. Why Dual-Engine (Deterministic Rule Engine + Bounded LLM)?
- **Problem**: LLM API calls take `300ms–1500ms` of network latency and require internet/API keys. Pure regex parsers can struggle with complex conversational grammar.
- **Decision**: Implement a Dual-Engine architecture with a deterministic regex/token parser as default (`<0.2ms` local compilation latency) and bounded LLM as conversational enhancer.
- **Benefit**: Provides 100% offline uptime, sub-millisecond local query compilation, and zero API costs for standard discovery.

---

## 3. Why Pydantic v2 for Ingress Validation?
- **Problem**: Unvalidated JSON payloads from LLMs or REST clients can cause runtime crashes in query builders.
- **Decision**: Use Pydantic v2 schemas (`SearchFilters`, `HousingSearchFilters`, `TriageQueryRequest`).
- **Benefit**: Immediate type coercion, constraint validation (`ge=0, le=100`), and canonical enum mapping (`CanonicalSpecialty`).

---

## 4. Why Decouple FastAPI from Streamlit?
- **Problem**: Streamlit apps are single-process monoliths that cannot easily serve external web/mobile clients or handle headless API traffic.
- **Decision**: Build a standalone REST API in `api.py` with OpenAPI docs at `/docs`.
- **Benefit**: The discovery and query engine can now be consumed by any external React/Vite frontend, mobile app, or backend microservice.

---

## 5. Why Non-Destructive Additive Schema Migrations (`ALTER TABLE`)?
- **Problem**: Naive schema checks that drop and recreate tables discard live user state (such as confirmed appointment bookings).
- **Decision**: `init_database` inspects columns via `PRAGMA table_info` and issues non-destructive `ALTER TABLE ... ADD COLUMN` statements for new schema attributes.
- **Benefit**: Data continuity is preserved across restarts; table drop/recreation is restricted strictly to explicit `force_reset=True` developer resets.

---

## 6. Why Fail-Closed Defaults and Single-Worker In-Memory Constraints?
- **Problem**: Security systems that fail open expose unprotected endpoints if misconfigured. In-memory rate limiters distributed across uncoordinated multi-process workers silently fail to enforce global limits.
- **Decision**: Enforce fail-closed authentication (`MEDDATA_ALLOW_UNAUTHENTICATED_DEMO=false` by default, rejecting unkeyed traffic with 503), bind uvicorn to `--workers 1` for consistent in-memory rate limiting, and restrict `X-Forwarded-For` trust to known proxy IPs.
- **Benefit**: Zero accidental public exposure in production, deterministic sliding-window rate tracking, and resistance to IP spoofing bypasses.

