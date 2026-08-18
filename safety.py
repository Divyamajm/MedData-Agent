"""
MedData AI & UrbanLocate - Multi-Domain Safety & Guardrails Layer
Implements medical safety boundaries, emergency triage separation, 
unknown database field detectors, prompt injection defenses, and SQL sandbox validation.
"""

import re
from typing import Tuple, Optional, Dict, Any, List

# Strict list of disallowed SQL mutation & DDL tokens for the sandbox
FORBIDDEN_SQL_TOKENS = {
    "DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "ATTACH", "DETACH",
    "PRAGMA", "EXEC", "EXECUTE", "TRUNCATE", "REPLACE", "GRANT", "REVOKE",
    "VACUUM", "REINDEX", "COMMIT", "ROLLBACK", "SAVEPOINT", "RELEASE"
}

# Known database columns in Doctors and Properties tables
DATABASE_KNOWN_FIELDS = {
    "name", "specialty", "primary_surgery", "surgery_success_rate", 
    "satisfaction_score", "distance_miles", "consultation_fee", 
    "is_available_today", "next_available_date", "id", "latitude", "longitude",
    "title", "neighborhood", "property_type", "price_per_month", "bedrooms", 
    "bathrooms", "sqft", "crime_index_score", "school_rating", "hospital_dist_miles",
    "transit_dist_miles", "market_dist_miles", "livability_score"
}

# Patterns indicating clinical diagnosis or prescription requests
MEDICAL_DIAGNOSIS_PATTERNS = [
    r"\b(do i have|could i have|am i having)\s+(cancer|stroke|heart attack|diabetes|infection|tumor|disease)\b",
    r"\b(what disease|what illness|what condition)\s+(do i have|is this)\b",
    r"\b(diagnose|diagnosis of|diagnose me)\b",
    r"\b(what medicine|which medicine|what medication|what drug)\s+(should i take|can i take|to take)\b",
    r"\b(what dosage|what dose|how much dosage|how many pills|how many mg)\b",
    r"\b(should i take|can i take)\s+[a-zA-Z0-9\s]+\s*(for|to treat)?\b",
    r"\b(prescribe|prescription for|cure my|remedy for)\b",
    r"\b(why does my\s+[a-zA-Z\s]+\s*hurt)\b",
    r"\b(am i sick|symptoms of [a-zA-Z\s]+ mean)\b"
]

# Patterns indicating an active life-threatening emergency
ACUTE_EMERGENCY_PATTERNS = [
    r"\b(i am having|i'm having|experiencing)\s+(a heart attack|severe chest pain|a stroke|an emergency|severe bleeding|trouble breathing|difficulty breathing)\b",
    r"\b(help me i am dying|i can't breathe|someone is unconscious|severe allergic reaction|anaphylaxis)\b",
    r"\b(emergency right now|life threatening|urgent emergency)\b"
]

# Patterns asking for healthcare attributes that do NOT exist in our SQLite schema
UNKNOWN_HEALTHCARE_ATTRIBUTE_PATTERNS = [
    (r"\b(speak|speaks|speaking|language|languages|spanish|hindi|french|mandarin|arabic)\b", "Doctor spoken languages"),
    (r"\b(how many surgeries|performed \d+ surgeries|surgery count|surgery volume|number of procedures)\b", "Surgery volume / total procedure count"),
    (r"\b(\d+\s*years?(?:\s*of)?\s*experience|years of experience|how many years|experience years|how long.*practiced)\b", "Years of experience / graduation year"),
    (r"\b(good with diabetic|diabetic patients|diabetes specialist|pediatric oncology|cancer subspecialist)\b", "Sub-specialty condition expertise (e.g. Diabetes)"),
    (r"\b(most patients|patient volume|number of patients|how many patients)\b", "Patient volume / total patient count"),
    (r"\b(board certified|certifications|fellowship|medical school|alumni|education)\b", "Medical school / Board certifications"),
    (r"\b(reviews|patient ratings text|written reviews|testimonials)\b", "Written patient review text (only satisfaction score is tracked)")
]

# Prompt injection markers
PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|your|the)\s+(instructions|rules|filters)",
    r"disregard\s+(the\s+)?(prompt|system|guidelines)",
    r"show\s+(me\s+)?(all\s+)?(database\s+)?secrets",
    r"bypass\s+(the\s+)?(guardrails|filters|sql)",
    r"give\s+me\s+(the\s+)?raw\s+sql",
    r"you\s+are\s+now\s+in\s+dan\s+mode",
    r"jailbreak"
]


def check_medical_advice_refusal(prompt: str) -> Optional[Dict[str, Any]]:
    """
    Checks if the user prompt is attempting to get a clinical diagnosis,
    symptom evaluation, or prescription/dosage advice.
    """
    prompt_clean = prompt.lower().strip()
    for pattern in MEDICAL_DIAGNOSIS_PATTERNS:
        if re.search(pattern, prompt_clean):
            return {
                "blocked": True,
                "reason": "medical_advice",
                "message": (
                    "⚠️ **Medical Safety Notice**: I am an AI discovery and directory agent, "
                    "**not a licensed physician or clinical diagnostic system**.\n\n"
                    "I cannot diagnose medical conditions, evaluate personal symptoms, prescribe medications, "
                    "or recommend drug dosages.\n\n"
                    "👉 **What to do:** If you are feeling unwell or have specific health questions, please schedule "
                    "an evaluation with a qualified medical doctor or visit an urgent care center."
                )
            }
    return None


def check_acute_emergency(prompt: str) -> Optional[Dict[str, Any]]:
    """
    Detects if the user is in an active medical emergency (e.g., severe chest pain, can't breathe).
    Does NOT block distance queries like 'nearest cardiologist' or specialty 'Emergency department'.
    """
    prompt_clean = prompt.lower().strip()
    
    # Exclude discovery/search phrasing
    if any(term in prompt_clean for term in ["nearest", "closest", "how far", "cost", "fee", "doctors in emergency", "find doctor", "list", "house", "rent"]):
        if re.search(r"\b(nearest|closest|doctor|specialist|fee|cost|directory|list|how far|house|property)\b", prompt_clean):
            return None

    for pattern in ACUTE_EMERGENCY_PATTERNS:
        if re.search(pattern, prompt_clean):
            return {
                "is_emergency": True,
                "reason": "acute_emergency",
                "message": (
                    "🚨 **CRITICAL MEDICAL EMERGENCY WARNING** 🚨\n\n"
                    "If you or someone around you is experiencing a medical emergency, acute chest pain, severe bleeding, "
                    "or difficulty breathing:\n\n"
                    "📞 **IMMEDIATELY CALL 911 (US/Canada), 112 (EU/India), or your local emergency response number.**\n\n"
                    "⚠️ Do NOT wait for an AI chat response. Go directly to the nearest hospital Emergency Room."
                )
            }
    return None


def check_unknown_attributes(prompt: str) -> Optional[Dict[str, Any]]:
    """
    Checks if user is asking for attributes not tracked in our SQLite database.
    Refuses to hallucinate or guess missing fields.
    """
    prompt_clean = prompt.lower().strip()
    missing_fields = []

    for pattern, description in UNKNOWN_HEALTHCARE_ATTRIBUTE_PATTERNS:
        if re.search(pattern, prompt_clean):
            missing_fields.append(description)

    if missing_fields:
        fields_str = ", ".join(missing_fields)
        return {
            "is_unknown": True,
            "missing_fields": missing_fields,
            "message": (
                f"ℹ️ **Database Factuality Boundary**: The demo database does not contain information regarding: "
                f"**{fields_str}**.\n\n"
                "To maintain strict factual integrity, I will not guess or infer unrecorded attributes.\n\n"
                "📊 **Available Verified Fields in Healthcare Database:**\n"
                "* Doctor Name & Specialty\n"
                "* Primary Surgical Procedure & Success Rate (%)\n"
                "* Patient Satisfaction Score (0-100)\n"
                "* Distance (miles) & Fee ($)\n"
                "* Verified Geolocation Coordinates & Availability"
            )
        }
    return None


def check_prompt_injection(prompt: str) -> Optional[Dict[str, Any]]:
    """Detects adversarial jailbreak and system-prompt extraction attempts."""
    prompt_clean = prompt.lower().strip()
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, prompt_clean):
            return {
                "is_injection": True,
                "message": (
                    "🛡️ **System Guardrail Enforcement**: MedData operates under strict deterministic query constraints. "
                    "System prompts, secrets, and raw unvalidated SQL generation cannot be bypassed. "
                    "Please submit a valid discovery query."
                )
            }
    return None


def validate_sql_sandbox_query(query: str) -> Tuple[bool, str]:
    """
    Validates custom SQL queries for the live SQL Sandbox.
    Enforces strict read-only execution (SELECT / WITH CTE only).
    Rejects any mutation, DDL, or administrative commands across all tables.
    """
    if not query or not query.strip():
        return False, "Query cannot be empty."

    # Strip comments
    clean_query = re.sub(r"--.*", "", query)
    clean_query = re.sub(r"/\*.*?\*/", "", clean_query, flags=re.DOTALL).strip()

    if not clean_query:
        return False, "Query contains no executable statements."

    # Reject multiple statements separated by semicolon
    statements = [s.strip() for s in clean_query.split(";") if s.strip()]
    if len(statements) > 1:
        return False, "Security Violation: Multiple SQL statements are not permitted in the sandbox."

    first_stmt = statements[0]
    tokens = re.findall(r"\b[A-Za-z_]+\b", first_stmt.upper())

    if not tokens:
        return False, "Invalid SQL syntax."

    first_keyword = tokens[0]
    if first_keyword not in {"SELECT", "WITH", "EXPLAIN"}:
        return False, f"Security Violation: Sandbox only allows read-only SELECT or WITH statements. Statement starts with '{first_keyword}'."

    # Check for any forbidden mutation or administrative keywords
    for token in tokens:
        if token in FORBIDDEN_SQL_TOKENS:
            return False, f"Security Violation: Disallowed SQL keyword '{token}' detected. Write, DDL, and PRAGMA commands are strictly prohibited."

    return True, "Query verified as read-only safe."
