"""
MedData AI -- Bounded LLM Structured Intent Parser
===================================================
Uses LLM (Google Gemini / OpenAI / Groq) strictly at the input boundary to parse
free-text natural language queries into strongly-typed Pydantic filters.

ARCHITECTURAL SAFETY INVARIANT:
- The LLM NEVER generates or executes SQL.
- The LLM only outputs structured JSON conforming to the Pydantic schema.
- All outputs pass through the deterministic Pydantic validator, Safety Layer,
  and Parameterized SQL Query Engine before any database interaction.
"""

import json
import os
import re
import time
from typing import Optional, Dict, Any, Tuple
import requests

from models import (
    IntentType,
    DomainType,
    CanonicalSpecialty,
    SearchFilters,
    HousingSearchFilters,
    IntentClassificationResult
)
from safety import (
    check_acute_emergency,
    check_medical_advice_refusal,
    check_prompt_injection,
    check_unknown_attributes
)


SYSTEM_PROMPT = """You are a strictly bounded clinical and real-estate intent extraction engine.
Your sole job is to parse the user's natural language input into a structured JSON classification matching the schema below.

CRITICAL RULES:
1. NEVER output SQL or code.
2. NEVER diagnose, prescribe medication, or give clinical medical advice.
3. If the user asks for subjective ranking without metrics (e.g. "who is the best cardiologist?", "top college"), set "ambiguity_detected": true and provide a helpful "clarification_needed" message.
4. If the user query indicates a severe acute medical emergency (e.g. chest pain, heart attack, stroke, heavy bleeding, cannot breathe), set "intent": "emergency".
5. If the user seeks clinical diagnosis or medication advice, set "intent": "medical_advice".
6. If the user asks for unknown attributes not in the database (e.g. spoken language, doctor's years of experience, specific surgeries performed), set "intent": "unknown_attribute".

JSON SCHEMA TO RETURN:
{
  "domain": "healthcare" | "real_estate" | "dynamic_dataset",
  "intent": "doctor_search" | "housing_search" | "directory" | "ranking" | "distance" | "affordability" | "availability" | "ambiguous" | "contradiction" | "emergency" | "medical_advice" | "unknown_attribute" | "prompt_injection",
  "ambiguity_detected": boolean,
  "clarification_needed": string or null,
  "confidence": float (0.0 to 1.0),
  "filters": {
    "specialty": string or null (e.g. "Cardiology", "Neurology", "Orthopedics", "Dermatology", "Pediatrics", "General Medicine", "Oncology", "Psychiatry", "ENT", "Gynecology"),
    "max_distance": float or null,
    "max_fee": float or null,
    "available_today": boolean or null,
    "negated_specialties": [string]
  }
}
Return ONLY valid raw JSON with no surrounding markdown or explanation.
"""


def parse_intent_with_llm(
    query: str,
    api_key: Optional[str] = None,
    provider: str = "gemini",
    model_name: Optional[str] = None
) -> Tuple[Optional[IntentClassificationResult], float, Optional[str]]:
    """
    Calls an LLM API to extract structured intent from raw text.
    Returns (IntentClassificationResult, latency_ms, error_msg).
    """
    start_time = time.perf_counter()
    
    # 1. First run deterministic instant safety pre-checks
    is_injection, inj_reason = check_prompt_injection(query)
    if is_injection:
        latency = (time.perf_counter() - start_time) * 1000
        return IntentClassificationResult(
            raw_prompt=query,
            domain=DomainType.HEALTHCARE,
            intent=IntentType.PROMPT_INJECTION,
            ambiguity_detected=False,
            confidence=1.0,
            filters=SearchFilters(),
            explanation=f"Blocked by deterministic security pre-screen: {inj_reason}"
        ), latency, None

    em_check = check_acute_emergency(query)
    if em_check and em_check.get("is_emergency"):
        latency = (time.perf_counter() - start_time) * 1000
        return IntentClassificationResult(
            raw_prompt=query,
            domain=DomainType.HEALTHCARE,
            intent=IntentType.EMERGENCY,
            ambiguity_detected=False,
            confidence=1.0,
            filters=SearchFilters(),
            explanation=em_check.get("message", "Direct emergency protocol activation.")
        ), latency, None

    med_check = check_medical_advice_refusal(query)
    if med_check and med_check.get("blocked"):
        latency = (time.perf_counter() - start_time) * 1000
        return IntentClassificationResult(
            raw_prompt=query,
            domain=DomainType.HEALTHCARE,
            intent=IntentType.MEDICAL_ADVICE,
            ambiguity_detected=False,
            confidence=1.0,
            filters=SearchFilters(),
            explanation=med_check.get("message", "Clinical diagnosis refusal.")
        ), latency, None

    unk_check = check_unknown_attributes(query)
    if unk_check and unk_check.get("is_unknown"):
        latency = (time.perf_counter() - start_time) * 1000
        return IntentClassificationResult(
            raw_prompt=query,
            domain=DomainType.HEALTHCARE,
            intent=IntentType.UNKNOWN_ATTRIBUTE,
            ambiguity_detected=False,
            confidence=1.0,
            filters=SearchFilters(),
            explanation=unk_check.get("message", "Untracked attribute refusal.")
        ), latency, None

    # Resolve API Key from argument or environment
    key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY") or os.environ.get("GROQ_API_KEY")
    if not key:
        return None, 0.0, "No API key found in parameters or environment (GEMINI_API_KEY/OPENAI_API_KEY)."

    try:
        # Determine provider and endpoint
        if provider.lower() in ["gemini", "google"] or "AIza" in key:
            model = model_name or "gemini-2.0-flash"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [
                    {"role": "user", "parts": [{"text": f"{SYSTEM_PROMPT}\n\nUSER INPUT:\n{query}"}]}
                ],
                "generationConfig": {
                    "temperature": 0.0,
                    "responseMimeType": "application/json"
                }
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=10)
            if resp.status_code != 200:
                return None, (time.perf_counter() - start_time) * 1000, f"Gemini API error {resp.status_code}: {resp.text}"
            
            data = resp.json()
            raw_json_str = data["candidates"][0]["content"]["parts"][0]["text"]

        else:
            # Standard OpenAI / Groq compatible endpoint
            model = model_name or "gpt-4o-mini"
            base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1/chat/completions")
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}"
            }
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": query}
                ],
                "temperature": 0.0,
                "response_format": {"type": "json_object"}
            }
            resp = requests.post(base_url, headers=headers, json=payload, timeout=10)
            if resp.status_code != 200:
                return None, (time.perf_counter() - start_time) * 1000, f"OpenAI API error {resp.status_code}: {resp.text}"
            
            data = resp.json()
            raw_json_str = data["choices"][0]["message"]["content"]

        # Clean JSON string
        cleaned_json = raw_json_str.strip()
        if cleaned_json.startswith("```json"):
            cleaned_json = cleaned_json[7:]
        if cleaned_json.startswith("```"):
            cleaned_json = cleaned_json[3:]
        if cleaned_json.endswith("```"):
            cleaned_json = cleaned_json[:-3]
        parsed_dict = json.loads(cleaned_json.strip())

        # Validate with Pydantic
        filters_dict = parsed_dict.get("filters", {})
        spec_str = filters_dict.get("specialty")
        canonical_spec = None
        if spec_str:
            for member in CanonicalSpecialty:
                if member.value.lower() == spec_str.lower() or member.name.lower() == spec_str.lower():
                    canonical_spec = member
                    break

        search_filters = SearchFilters(
            specialty=canonical_spec,
            max_distance=filters_dict.get("max_distance"),
            max_fee=filters_dict.get("max_fee"),
            available_today=filters_dict.get("available_today", False) if filters_dict.get("available_today") is not None else False
        )

        intent_val = parsed_dict.get("intent", "doctor_search")
        try:
            intent_enum = IntentType(intent_val)
        except ValueError:
            intent_enum = IntentType.DOCTOR_SEARCH

        domain_val = parsed_dict.get("domain", "healthcare")
        try:
            domain_enum = DomainType(domain_val)
        except ValueError:
            domain_enum = DomainType.HEALTHCARE

        result = IntentClassificationResult(
            raw_prompt=query,
            domain=domain_enum,
            intent=intent_enum,
            ambiguity_detected=parsed_dict.get("ambiguity_detected", False),
            ambiguity_reason=parsed_dict.get("clarification_needed"),
            confidence=float(parsed_dict.get("confidence", 0.95)),
            filters=search_filters,
            explanation=f"LLM-parsed intent ({provider.upper()}) verified by Pydantic schema."
        )

        latency = (time.perf_counter() - start_time) * 1000
        return result, latency, None

    except Exception as e:
        latency = (time.perf_counter() - start_time) * 1000
        return None, latency, f"LLM Parsing failed: {str(e)}"
