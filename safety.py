"""
MedData AI & UrbanLocate - Multi-Tier Safety Guardrails Layer
Provides clinical medical safety checks, emergency protocol triggers,
unknown attribute boundary enforcement, and token-based read-only SQL sandboxing.
"""

import re
from typing import Dict, Any, Optional, Tuple, List


# Healthcare database allowable fields
ALLOWED_DOCTOR_COLUMNS = {
    "id", "name", "specialty", "primary_surgery", "surgery_success_rate",
    "satisfaction_score", "distance_miles", "consultation_fee",
    "is_available_today", "next_available_date", "latitude", "longitude"
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
    r"\b(do i have|could i have|am i having|is it possible i have)\s+(cancer|stroke|heart attack|diabetes|infection|tumor|disease|covid|arthritis|hypertension)\b",
    r"\b(what disease|what illness|what condition|causes of|what causes)\s+(do i have|is this|left arm|numbness|chest ache|pain)\b",
    r"\b(diagnose|diagnosis of|diagnose me|diagnose my|can you diagnose)\b",
    r"\b(what medicine|which medicine|what medication|what drug|which drug)\s+(should i take|can i take|to take|for|recommended|treats|prescribe)\b",
    r"\b(what dosage|what dose|how much dosage|how many pills|how many mg|how much mg|dosage of)\b",
    r"\b(should i take|can i take)\s+[a-zA-Z0-9\s]+\s*(for|to treat|with|and)?\b",
    r"\b(prescribe|prescription for|cure my|remedy for|cure for|home remedies|cure diabetes|cure migraine|cure cancer|treat diabetes|treats migraine|treats asthma)\b",
    r"\b(why does my\s+[a-zA-Z\s]+\s*hurt)\b",
    r"\b(am i sick|symptoms of [a-zA-Z\s]+ mean|symptoms mean)\b",
    r"\b(how to cure|how to treat)\s+[a-zA-Z\s]+\s*(naturally)?\b",
    r"\b(is my [a-zA-Z\s]+ arthritis|is this arthritis|is my pain arthritis)\b"
]

# Patterns indicating an active life-threatening emergency
ACUTE_EMERGENCY_PATTERNS = [
    r"\b(i am having|i'm having|experiencing|having a|having|struggling to|cannot|can't)\s+(a heart attack|severe chest pain|a stroke|an emergency|severe bleeding|trouble breathing|difficulty breathing|shortness of breath|heart attack right now|stroke|breathe)\b",
    r"\b(help me i am dying|i can't breathe|cannot breathe|unconscious|not responding|collapsed|lost consciousness|severe allergic reaction|anaphylaxis|anaphylactic|chest feels tight|tightness in chest|severe chest pain)\b",
    r"\b(emergency right now|life threatening|urgent emergency|arterial bleeding|choking|slurred speech stroke|swallowed poison|poison chemical|head trauma bleeding|uncontrollable seizure|uncontrolled bleeding|heavy bleeding|bleeding heavily|need ambulance|ambulance right now|swelling face|throat closing)\b",
    r"\b(patient is unconscious|person collapsed|friend is having a stroke|mother lost consciousness|baby is choking|acute heart attack)\b"
]

# Patterns asking for healthcare attributes that do NOT exist in our SQLite schema
UNKNOWN_HEALTHCARE_ATTRIBUTE_PATTERNS = [
    (r"\b(speak|speaks|speaking|language|languages|spanish|hindi|french|mandarin|arabic|tamil|german|telugu)\b", "Doctor spoken languages"),
    (r"\b(how many surgeries|performed \d+ surgeries|surgery count|surgery volume|number of procedures|total surgeries completed|completed \d+ surgeries|robotic surgeries)\b", "Surgery volume / total procedure count"),
    (r"\b(\d+\s*years?(?:\s*of)?\s*experience|years of experience|how many years|experience years|how long.*practiced)\b", "Years of experience / graduation year"),
    (r"\b(good with diabetic|diabetic patients|diabetes specialist|pediatric oncology|cancer subspecialist)\b", "Sub-specialty condition expertise (e.g. Diabetes)"),
    (r"\b(most patients|patient volume|number of patients|how many patients|patient volume treated)\b", "Patient volume / total patient count"),
    (r"\b(board certified|certifications|fellowship|medical school|alumni|education|harvard|aiims|graduated from|attended aiims)\b", "Medical school / Board certifications"),
    (r"\b(reviews|patient ratings text|written reviews|testimonials|patient testimonials)\b", "Written patient review text (only satisfaction score is tracked)"),
    (r"\b(marital status|hobbies|robotic surgery|marble flooring|zodiac|graduation year)\b", "Non-schema attribute (untracked field)")
]

# Prompt injection markers
PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|your|the)\s+(instructions|rules|filters)",
    r"disregard\s+(the\s+)?(prompt|system|guidelines|what you were told)",
    r"show\s+(me\s+)?(all\s+)?(database\s+)?secrets",
    r"bypass\s+(the\s+)?(guardrails|filters|sql|safety\s+filters)",
    r"give\s+me\s+(the\s+)?raw\s+sql",
    r"system\s+override",
    r"drop\s+all\s+tables",
    r"output\s+raw\s+database\s+secrets",
    r"you\s+are\s+now\s+(in\s+)?dan(\s+mode)?",
    r"jailbreak",
    r"sqlite_master",
    r"system prompt",
    r"print schema",
    r"reveal api keys",
    r"admin table",
    r"output internal instructions"
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
    Does NOT block discovery queries like 'nearest cardiologist' or specialty 'Emergency department'.
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
    Identifies if user is asking for columns/fields that do NOT exist in the SQLite schema.
    Returns factuality warning instead of guessing.
    """
    prompt_clean = prompt.lower().strip()
    missing_fields = []

    for pattern, field_desc in UNKNOWN_HEALTHCARE_ATTRIBUTE_PATTERNS:
        if re.search(pattern, prompt_clean):
            missing_fields.append(field_desc)

    if missing_fields:
        fields_str = ", ".join(missing_fields)
        return {
            "is_unknown": True,
            "missing_fields": missing_fields,
            "message": (
                f"ℹ️ **Database Factuality Boundary**: The demo database does not contain information regarding: "
                f"**{fields_str}**.\n\n"
                "To maintain strict factual integrity, I will not guess or infer unrecorded attributes.\n\n"
                "📊 **Available Ground-Truth Fields in Healthcare Database:**\n"
                "* Doctor Name & Specialty\n"
                "* Primary Surgical Procedure & Success Rate (%)\n"
                "* Patient Satisfaction Score (0-100)\n"
                "* Distance (miles) & Fee (₹ / INR)\n"
                "* Geolocation Coordinates & Availability"
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


# Allowed tables for ad-hoc read-only SQL querying
ALLOWED_SANDBOX_TABLES = {"DOCTORS", "PROPERTIES", "APPOINTMENTS", "SPECIALTIES"}

# Forbidden system tables to prevent internal schema leaks
FORBIDDEN_SYSTEM_TABLES = {
    "SQLITE_MASTER", "SQLITE_SCHEMA", "SQLITE_TEMP_MASTER", "SQLITE_TEMP_SCHEMA",
    "SQLITE_SEQUENCE", "SQLITE_STAT1", "SQLITE_STAT2", "SQLITE_STAT3", "SQLITE_STAT4",
    "INFORMATION_SCHEMA", "PG_CATALOG", "PG_TABLES", "SYS", "MYSQL"
}


def validate_sql_sandbox_query(query: str) -> Tuple[bool, str]:
    """
    Validates custom SQL queries for the live SQL Sandbox using AST analysis.
    Enforces strict read-only execution (SELECT / WITH CTE / EXPLAIN only).
    Rejects any mutation, DDL, administrative commands, system catalog reads,
    and recursive CTE resource-exhaustion vectors across the entire AST.
    """
    if not query or not query.strip():
        return False, "Query cannot be empty."

    # Strip comments
    clean_query = re.sub(r"--.*", "", query)
    clean_query = re.sub(r"/\*.*?\*/", "", clean_query, flags=re.DOTALL).strip()

    if not clean_query:
        return False, "Query contains no executable statements."

    # 1. Parse AST with sqlglot
    try:
        import sqlglot
        import sqlglot.expressions as exp
        
        try:
            parsed_statements = sqlglot.parse(clean_query, read="sqlite")
        except Exception as e:
            return False, f"SQL Syntax Error: Unable to parse query AST ({str(e)})."

        if not parsed_statements or parsed_statements[0] is None:
            return False, "Query contains no executable SQL statements."

        if len(parsed_statements) > 1:
            return False, "Multi-statement queries (separated by ';') are forbidden in the read-only sandbox."

        tree = parsed_statements[0]

        # Handle EXPLAIN statements
        if tree.key == "command":
            cmd_text = str(tree.this).strip().upper()
            if not cmd_text.startswith("EXPLAIN"):
                return False, f"Security Violation: Command '{cmd_text}' is forbidden in read-only sandbox."
            return True, "EXPLAIN query passed read-only security validation."

        # Enforce read-only statement type
        if not isinstance(tree, (exp.Select, exp.Union, exp.Query)):
            return False, f"Security Violation: Sandbox only allows read-only SELECT, WITH, or EXPLAIN statements. Received '{type(tree).__name__}'."

        # Block recursive CTEs
        with_exp = tree.find(exp.With)
        if with_exp and with_exp.args.get("recursive"):
            return False, "Security Violation: Recursive CTEs (WITH RECURSIVE) are forbidden in the read-only sandbox."

        # Collect declared CTE aliases
        declared_ctes = set()
        if hasattr(tree, "ctes"):
            for cte in tree.ctes:
                alias = getattr(cte, "alias_or_name", None) or getattr(cte, "alias", None)
                if alias:
                    declared_ctes.add(str(alias).upper())

        # Inspect all Table references across the entire AST (FROM, JOIN, comma joins, subqueries, CTE bodies)
        for t in tree.find_all(exp.Table):
            tbl_name = t.name.upper()
            if tbl_name in FORBIDDEN_SYSTEM_TABLES:
                return False, f"Security Violation: Access to system catalog table '{t.name}' is restricted."
            if tbl_name in declared_ctes or tbl_name in ALLOWED_SANDBOX_TABLES:
                continue
            return False, f"Security Violation: Table '{t.name}' is not in the sandbox allowlist ({', '.join(sorted(ALLOWED_SANDBOX_TABLES))})."

        # Block any mutation or administrative expressions in the AST
        forbidden_expr_types = (exp.Drop, exp.Delete, exp.Insert, exp.Update, exp.Alter, exp.Create)
        if any(tree.find_all(forbidden_expr_types)):
            return False, "Security Violation: Mutation or DDL statements are forbidden in the read-only sandbox."

        return True, "Query passed read-only AST and table allowlist validation."

    except ImportError:
        # Fallback to token validation if sqlglot is not present
        statements = [s.strip() for s in clean_query.split(";") if s.strip()]
        if len(statements) > 1:
            return False, "Multi-statement queries (separated by ';') are forbidden in the read-only sandbox."

        first_stmt = statements[0]
        tokens = re.findall(r"\b[A-Za-z_]+\b", first_stmt.upper())
        if not tokens or tokens[0] not in {"SELECT", "WITH", "EXPLAIN"}:
            return False, "Security Violation: Sandbox only allows read-only SELECT or WITH statements."

        forbidden_tokens = {"DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "TRUNCATE", "RECURSIVE"}
        for token in tokens:
            if token in forbidden_tokens:
                return False, f"Security Violation: Command '{token}' is forbidden."
            if token in FORBIDDEN_SYSTEM_TABLES:
                return False, f"Security Violation: Access to system table '{token}' is restricted."

        return True, "Query passed read-only security validation."
