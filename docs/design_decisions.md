# 💡 Architectural Design Decisions & Tradeoff Analysis

## 1. Why Bounded LLM vs Pure Text-to-SQL (Vanna/LangChain style)?
- **Problem**: Letting an LLM directly generate SQL strings leads to hallucinated column names, invalid joins, and critical SQL injection vulnerabilities.
- **Decision**: The LLM is restricted to outputting JSON matching our typed Pydantic schema (`SearchFilters`).
- **Benefit**: Parameterized SQL is generated 100% deterministically by `query_engine.py`. Even if the LLM output is adversarial, the compiler only uses parameterized placeholders (`?`) and allowlisted column names.

---

## 2. Why Dual-Engine (Deterministic AST + Bounded LLM)?
- **Problem**: LLM API calls take `300ms–700ms` and require internet/API keys. Pure regex parsers can struggle with complex conversational grammar.
- **Decision**: Implement a Dual-Engine architecture with deterministic regex as default (`<0.3ms` latency) and LLM as conversational enhancer.
- **Benefit**: Provides 100% offline uptime, sub-millisecond query compilation, and zero API costs for standard discovery.

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
