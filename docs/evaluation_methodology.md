# 📊 Scientific Evaluation Methodology & Benchmark Results

## Benchmark Dataset Composition (290 Labeled Test Cases)

The evaluation suite (`python -m tests.eval_benchmark`) executes a battery of 290 labeled multi-domain queries:

```
BENCHMARK DATASET (290 QUERIES)
├── Clinical Discovery & Specialty Search (30 queries)
├── Multi-Constraint Complex Queries (30 queries)
├── Exhaustive Directory Listings (25 queries)
├── Subjective & Ambiguous Queries (25 queries)
├── Acute Medical Emergencies (25 queries)
├── Clinical Diagnosis & Prescription Refusals (25 queries)
├── Unknown Schema Attributes / Out-of-Scope (25 queries)
├── Real Estate & Housing Discovery (30 queries)
├── Affordability & Free Consultations (15 queries)
├── Distance & Radius Proximity (10 queries)
├── Availability & Same-Day Openings (10 queries)
├── Negation Handling (10 queries)
├── Contradiction Detection (10 queries)
└── Security & Prompt Injection Defense (20 queries)
```

---

## Measured Performance Metrics

| Evaluation Metric | Measured Result | Benchmark Focus |
|---|:---:|---|
| **Intent Classification Accuracy** | **84.8%** | Multi-class intent routing across 14 intent types. |
| **Entity Extraction Precision** | **93.1%** | Specialty, fee boundaries, distance radius, and city matching. |
| **Clinical Safety Refusal Precision** | **96.3%** | Intercepting medical diagnosis, dosage, and acute symptoms without false positives. |
| **Clinical Safety Refusal Recall** | **82.1%** | Percentage of dangerous prompts successfully blocked. |
| **Ambiguity Interception Rate** | **98.3%** | Subjective queries (*"best doctor"*, *"top clinic"*) intercepted for metric clarification. |
| **SQL Execution Success Rate** | **100.0%** | Zero syntax errors, 100% database grounded execution. |

---

## Latency Distribution (Deterministic Pipeline)

*Tested on local benchmark environment (excluding external LLM network roundtrips):*

- **p50 (Median)**: `0.12 ms`
- **p95**: `0.34 ms`
- **p99**: `0.69 ms`
- **Mean Latency**: `0.15 ms`
