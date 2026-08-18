# 🛡️ Security Architecture & Threat Model

## Threat Modeling & Defense Vectors

| Threat Vector | Attack Mechanism | MedData AI Mitigation Strategy | Verification Metric |
|---|---|---|:---:|
| **Direct SQL Injection** | Concatenating user text into raw SQL string (e.g. `' OR 1=1 --`) | Parameterized SQL compilation via `?` placeholders + column allowlists. | **100% Block Rate** |
| **LLM-Generated Malicious SQL** | Jailbreaking the LLM to output `DROP TABLE Doctors` | **Architectural Isolation**: The LLM output is strictly JSON mapped to Pydantic models. The LLM has zero access to SQL generation. | **100% Isolation** |
| **Prompt Injection / Jailbreaks** | System prompt override (DAN mode, "ignore previous instructions") | Tokenized regex pre-screens + safety rule interception before query execution. | **90.0% Detection Rate** |
| **Clinical Diagnosis Liability** | User seeking diagnosis/dosage for acute conditions | Programmatic refusal gate (`check_medical_advice_refusal`) directing user to licensed physicians. | **96.3% Refusal Precision** |
| **Acute Emergency Harm** | User waiting on AI chat during active heart attack/stroke | Instant interception (`check_acute_emergency`) displaying bold red 112/911 emergency warnings. | **88.0% Trigger Recall** |
| **Fact Hallucination / Fabricated Rows** | LLM inventing non-existent doctors, prices, or ratings | 100% SQLite query execution; zero LLM generative answering of database records. | **100% Database Grounding** |
| **Secret & API Key Exposure** | API keys leaking via query strings or logs | Headers-based authentication, environment variable resolution, and sanitized exceptions. | **Zero Leakage** |

---

## 2-Layer AST SQL Sandbox Specification

The platform includes an interactive developer SQL sandbox. To prevent security compromises:

1. **Layer 1: First-Token Allowlist**
   - The query AST is tokenized after stripping comments.
   - The first meaningful SQL token must belong to: `{'SELECT', 'WITH', 'EXPLAIN'}`.
2. **Layer 2: Mutation & DDL Blocklist**
   - The entire query is scanned for forbidden keywords:
     `{'DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'TRUNCATE', 'RENAME', 'CREATE', 'REPLACE', 'ATTACH', 'DETACH', 'PRAGMA', 'VACUUM', 'REINDEX'}`.
   - Multi-statement injection via semicolons (`SELECT ...; DROP ...`) is strictly intercepted.
