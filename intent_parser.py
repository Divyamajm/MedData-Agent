"""
MedData AI - Intent Classification & Entity Extraction Layer
Provides deterministic NLP parsing, synonym normalization, negation handling,
multi-constraint extraction, ambiguity interception, and contradiction checking.
"""

import re
from typing import Dict, Any, List, Optional, Tuple

from models import (
    CanonicalSpecialty, SortMetric, SortOrder, IntentType,
    SearchFilters, IntentClassificationResult
)
from safety import (
    check_medical_advice_refusal, check_acute_emergency,
    check_unknown_attributes, check_prompt_injection
)

# Canonical mapping of colloquial phrases and synonyms to database specialties
SPECIALTY_SYNONYMS = {
    # Cardiology
    "cardiology": CanonicalSpecialty.CARDIOLOGY,
    "cardiologist": CanonicalSpecialty.CARDIOLOGY,
    "cardiologists": CanonicalSpecialty.CARDIOLOGY,
    "cardiac": CanonicalSpecialty.CARDIOLOGY,
    "heart doctor": CanonicalSpecialty.CARDIOLOGY,
    "heart doctors": CanonicalSpecialty.CARDIOLOGY,
    "heart specialist": CanonicalSpecialty.CARDIOLOGY,
    "heart specialists": CanonicalSpecialty.CARDIOLOGY,
    "heart surgeon": CanonicalSpecialty.CARDIOLOGY,
    "heart surgeons": CanonicalSpecialty.CARDIOLOGY,
    "cardio": CanonicalSpecialty.CARDIOLOGY,
    
    # Neurology
    "neurology": CanonicalSpecialty.NEUROLOGY,
    "neurologist": CanonicalSpecialty.NEUROLOGY,
    "neurologists": CanonicalSpecialty.NEUROLOGY,
    "neuro": CanonicalSpecialty.NEUROLOGY,
    "brain doctor": CanonicalSpecialty.NEUROLOGY,
    "brain doctors": CanonicalSpecialty.NEUROLOGY,
    "brain specialist": CanonicalSpecialty.NEUROLOGY,
    "brain specialists": CanonicalSpecialty.NEUROLOGY,
    "spine specialist": CanonicalSpecialty.NEUROLOGY,
    "spine specialists": CanonicalSpecialty.NEUROLOGY,
    "nerve doctor": CanonicalSpecialty.NEUROLOGY,
    "nerve doctors": CanonicalSpecialty.NEUROLOGY,
    
    # Orthopedics
    "orthopedics": CanonicalSpecialty.ORTHOPEDICS,
    "orthopedic": CanonicalSpecialty.ORTHOPEDICS,
    "orthopedist": CanonicalSpecialty.ORTHOPEDICS,
    "orthopedists": CanonicalSpecialty.ORTHOPEDICS,
    "orthopaedics": CanonicalSpecialty.ORTHOPEDICS,
    "ortho": CanonicalSpecialty.ORTHOPEDICS,
    "bone doctor": CanonicalSpecialty.ORTHOPEDICS,
    "bone doctors": CanonicalSpecialty.ORTHOPEDICS,
    "bone specialist": CanonicalSpecialty.ORTHOPEDICS,
    "bone specialists": CanonicalSpecialty.ORTHOPEDICS,
    "joint doctor": CanonicalSpecialty.ORTHOPEDICS,
    "joint doctors": CanonicalSpecialty.ORTHOPEDICS,
    "joint specialist": CanonicalSpecialty.ORTHOPEDICS,
    "joint specialists": CanonicalSpecialty.ORTHOPEDICS,
    "knee doctor": CanonicalSpecialty.ORTHOPEDICS,
    "knee doctors": CanonicalSpecialty.ORTHOPEDICS,
    "hip doctor": CanonicalSpecialty.ORTHOPEDICS,
    "hip doctors": CanonicalSpecialty.ORTHOPEDICS,
    
    # Pediatrics
    "pediatrics": CanonicalSpecialty.PEDIATRICS,
    "pediatrician": CanonicalSpecialty.PEDIATRICS,
    "pediatricians": CanonicalSpecialty.PEDIATRICS,
    "paediatrics": CanonicalSpecialty.PEDIATRICS,
    "paediatrician": CanonicalSpecialty.PEDIATRICS,
    "paediatricians": CanonicalSpecialty.PEDIATRICS,
    "children's doctor": CanonicalSpecialty.PEDIATRICS,
    "children's doctors": CanonicalSpecialty.PEDIATRICS,
    "children doctor": CanonicalSpecialty.PEDIATRICS,
    "children doctors": CanonicalSpecialty.PEDIATRICS,
    "child doctor": CanonicalSpecialty.PEDIATRICS,
    "child doctors": CanonicalSpecialty.PEDIATRICS,
    "child specialist": CanonicalSpecialty.PEDIATRICS,
    "child specialists": CanonicalSpecialty.PEDIATRICS,
    "kids doctor": CanonicalSpecialty.PEDIATRICS,
    "kids doctors": CanonicalSpecialty.PEDIATRICS,
    "infant doctor": CanonicalSpecialty.PEDIATRICS,
    "infant doctors": CanonicalSpecialty.PEDIATRICS,
    
    # Emergency
    "emergency": CanonicalSpecialty.EMERGENCY,
    "emergency doctor": CanonicalSpecialty.EMERGENCY,
    "emergency doctors": CanonicalSpecialty.EMERGENCY,
    "emergency room doctor": CanonicalSpecialty.EMERGENCY,
    "emergency room doctors": CanonicalSpecialty.EMERGENCY,
    "er doctor": CanonicalSpecialty.EMERGENCY,
    "er doctors": CanonicalSpecialty.EMERGENCY,
    "trauma doctor": CanonicalSpecialty.EMERGENCY,
    "trauma doctors": CanonicalSpecialty.EMERGENCY,
    "trauma specialist": CanonicalSpecialty.EMERGENCY,
    "trauma specialists": CanonicalSpecialty.EMERGENCY,
    "emergency physician": CanonicalSpecialty.EMERGENCY,
    "emergency physicians": CanonicalSpecialty.EMERGENCY,
    "emergency department": CanonicalSpecialty.EMERGENCY
}

NEGATION_TRIGGERS = [
    r"\b(don't need|do not need|don't want|do not want|not looking for|no need for|no|not|without|exclude|except|other than)\s+([a-zA-Z0-9\s]+)"
]


def extract_negations(prompt: str) -> List[str]:
    """Identifies terms that the user explicitly negated."""
    negated = []
    prompt_lower = prompt.lower()
    for pattern in NEGATION_TRIGGERS:
        matches = re.finditer(pattern, prompt_lower)
        for m in matches:
            negated_phrase = m.group(2).strip()
            negated.append(negated_phrase)
    return negated


def extract_specialty(prompt: str, negated_phrases: List[str]) -> Tuple[Optional[CanonicalSpecialty], Optional[str], bool]:
    """
    Extracts canonical medical specialty from prompt.
    Returns: (canonical_specialty, matched_synonym, is_negated)
    """
    prompt_lower = prompt.lower()
    
    # Sort synonyms by length descending to match multi-word phrases first
    sorted_synonyms = sorted(SPECIALTY_SYNONYMS.items(), key=lambda x: len(x[0]), reverse=True)
    
    for phrase, canonical in sorted_synonyms:
        pattern = r"\b" + re.escape(phrase) + r"\b"
        if re.search(pattern, prompt_lower):
            # Check if this occurrence was negated
            is_negated = False
            for neg in negated_phrases:
                if phrase in neg:
                    is_negated = True
                    break
            
            if is_negated:
                return canonical, phrase, True
            else:
                return canonical, phrase, False
                
    return None, None, False


def extract_numeric_constraints(prompt: str) -> Dict[str, Any]:
    """Extracts max distance, max fee, min satisfaction, min success rate, and row limit."""
    prompt_lower = prompt.lower()
    constraints = {}

    # Distance patterns: "within 5 miles", "under 10 miles", "max 15 mi", "< 5 miles", "5 miles"
    dist_match = re.search(r"(?:within|under|less than|max|maximum|up to|<|<=)?\s*(\d+(?:\.\d+)?)\s*(?:miles|mile|mi)\b", prompt_lower)
    if dist_match:
        val = float(dist_match.group(1))
        constraints["max_distance"] = val

    # Fee / Price patterns: "$100", "under $150", "max 200 dollars", "<= $50", "fee under 100"
    fee_match = re.search(r"(?:fee|cost|price|under|less than|max|maximum|up to|<|<=)?\s*\$\s*(\d+)\b", prompt_lower)
    if not fee_match:
        fee_match = re.search(r"(?:under|less than|max|maximum|up to|<|<=)\s*(\d+)\s*(?:dollars|usd|bucks)\b", prompt_lower)
    if fee_match:
        constraints["max_fee"] = int(fee_match.group(1))

    # Free care explicit check
    if re.search(r"\b(free|no cost|\$0)\b", prompt_lower):
        constraints["max_fee"] = 0

    # Success rate patterns: "success rate over 95%", "> 90% success", "95% success rate"
    succ_match = re.search(r"(?:success|success rate|surgical rate)\s*(?:over|above|greater than|>|>=|at least)?\s*(\d+(?:\.\d+)?)\s*%", prompt_lower)
    if not succ_match:
        succ_match = re.search(r"(\d+(?:\.\d+)?)\s*%\s*(?:success|success rate)", prompt_lower)
    if succ_match:
        constraints["min_success_rate"] = float(succ_match.group(1))

    # Satisfaction score patterns: "satisfaction score over 90", "satisfaction > 85", "score at least 90"
    sat_match = re.search(r"(?:satisfaction|satisfaction score|rating)\s*(?:over|above|greater than|>|>=|at least)\s*(\d+)\b", prompt_lower)
    if sat_match:
        constraints["min_satisfaction"] = int(sat_match.group(1))

    # Result limit / count patterns: "top 3", "first 10", "show 5"
    limit_match = re.search(r"\b(?:top|first|show|limit|give me)\s*(\d+)\b", prompt_lower)
    if limit_match:
        constraints["limit"] = int(limit_match.group(1))

    # Availability pattern
    if re.search(r"\b(available today|today only|open today|see someone today|available now)\b", prompt_lower):
        constraints["available_today"] = True

    return constraints


def parse_intent_and_filters(prompt: str) -> IntentClassificationResult:
    """
    Main deterministic NLP pipeline for classifying intent, extracting entities,
    intercepting ambiguities, and detecting contradictions.
    """
    raw_prompt = prompt.strip()
    prompt_lower = raw_prompt.lower()

    # 1. Prompt Injection Defense
    injection = check_prompt_injection(raw_prompt)
    if injection:
        return IntentClassificationResult(
            intent=IntentType.PROMPT_INJECTION,
            confidence=1.0,
            safety_flags=["prompt_injection"],
            explanation=injection["message"],
            raw_prompt=raw_prompt
        )

    # 2. Medical Advice & Diagnosis Guardrail
    med_refusal = check_medical_advice_refusal(raw_prompt)
    if med_refusal:
        return IntentClassificationResult(
            intent=IntentType.MEDICAL_ADVICE,
            confidence=1.0,
            safety_flags=["medical_advice_refusal"],
            explanation=med_refusal["message"],
            raw_prompt=raw_prompt
        )

    # 3. Acute Life-Threatening Emergency Guardrail
    acute_emerg = check_acute_emergency(raw_prompt)
    if acute_emerg:
        return IntentClassificationResult(
            intent=IntentType.EMERGENCY,
            confidence=1.0,
            safety_flags=["acute_emergency"],
            explanation=acute_emerg["message"],
            raw_prompt=raw_prompt
        )

    # 4. Unknown Database Fields Guardrail (Refusal to Guess)
    unknown_attr = check_unknown_attributes(raw_prompt)
    if unknown_attr:
        return IntentClassificationResult(
            intent=IntentType.UNKNOWN_ATTRIBUTE,
            confidence=1.0,
            unknown_fields_requested=unknown_attr["missing_fields"],
            explanation=unknown_attr["message"],
            raw_prompt=raw_prompt
        )

    # 5. Greeting / Intro
    if re.match(r"^(hi|hello|hey|greetings|good morning|good afternoon|good evening|howdy)\b", prompt_lower) and len(prompt_lower.split()) <= 4:
        return IntentClassificationResult(
            intent=IntentType.GREETING,
            confidence=1.0,
            explanation=(
                "Hello! I am the **MedData AI Triage & Discovery Agent**.\n\n"
                "I can help you search our verified demo physician directory by:\n"
                "• **Specialty** (Cardiology, Neurology, Orthopedics, Pediatrics, Emergency)\n"
                "• **Cost & Affordability** (e.g., *'Find free or cheap doctors'*)\n"
                "• **Distance & Location** (e.g., *'Nearest cardiologist within 5 miles'*)\n"
                "• **Clinical Success Rate & Satisfaction** (e.g., *'Top doctors by surgical success rate'*)\n"
                "• **Availability** (e.g., *'Who is available today?'*)\n\n"
                "How may I assist you today?"
            ),
            raw_prompt=raw_prompt
        )

    # 6. Entity & Negation Extraction
    negated_phrases = extract_negations(raw_prompt)
    specialty, matched_synonym, is_negated = extract_specialty(raw_prompt, negated_phrases)
    numeric_constraints = extract_numeric_constraints(raw_prompt)

    normalized_entities = {}
    negated_entities = []

    if specialty:
        if is_negated:
            negated_entities.append(f"Specialty: {specialty.value} (from '{matched_synonym}')")
        else:
            normalized_entities["specialty"] = specialty.value
            if matched_synonym != specialty.value.lower():
                normalized_entities["synonym_interpretation"] = f"Interpreted '{matched_synonym}' as {specialty.value}"

    # 7. Contradiction Detection
    contradictions = []
    
    # Contradiction: Free ($0) vs $500 fee
    has_free = bool(re.search(r"\b(free|\$0|zero dollars)\b", prompt_lower))
    has_high_fee = bool(re.search(r"\$\s*([1-9]\d{2,})", prompt_lower))
    if has_free and has_high_fee:
        high_fee_val = re.search(r"\$\s*([1-9]\d{2,})", prompt_lower).group(1)
        contradictions.append(
            f"Contradictory fee criteria: You requested a 'free' ($0) consultation, but also specified a ${high_fee_val} fee limit."
        )

    # Contradiction: Distance <= 0
    if numeric_constraints.get("max_distance") is not None and numeric_constraints["max_distance"] <= 0:
        contradictions.append("Contradictory distance: Search radius cannot be 0 or negative miles.")

    if contradictions:
        return IntentClassificationResult(
            intent=IntentType.CONTRADICTION,
            confidence=1.0,
            contradictions_detected=contradictions,
            explanation=(
                "⚠️ **Contradictory Request Detected**:\n\n" +
                "\n".join([f"• {c}" for c in contradictions]) +
                "\n\nPlease clarify your search criteria so I can provide accurate database results."
            ),
            raw_prompt=raw_prompt
        )

    # 8. Check for Specific Doctor Name Inquiry
    doc_name_match = re.search(r"\b(dr\.?\s+[a-z]+(?:\s+[a-z]+)?)\b", prompt_lower)
    if doc_name_match and "find" not in prompt_lower and "search" not in prompt_lower:
        doc_name_str = doc_name_match.group(1).title()
        # Verify it's not just "Dr."
        if len(doc_name_str.split()) >= 2:
            return IntentClassificationResult(
                intent=IntentType.DOCTOR_DETAILS,
                confidence=0.95,
                filters=SearchFilters(doctor_name=doc_name_str),
                normalized_entities={"doctor_name": doc_name_str},
                explanation=f"Fetching verified database record for {doc_name_str}.",
                raw_prompt=raw_prompt
            )

    # 9. Ranking Ambiguity Detection ("Best", "Top", "Greatest", "Preferred")
    has_ranking_keyword = bool(re.search(r"\b(best|top|greatest|highest rated|number one|most recommended|finest)\b", prompt_lower))
    
    # Check if a specific optimization metric was already explicitly mentioned
    has_explicit_satisfaction = bool(re.search(r"\b(satisfaction|patient score|rating|reviews? score)\b", prompt_lower))
    has_explicit_success = bool(re.search(r"\b(success rate|surgical success|surgery rate|outcomes?)\b", prompt_lower))
    has_explicit_distance = bool(re.search(r"\b(nearest|closest|shortest distance|proximity|near me)\b", prompt_lower))
    has_explicit_price = bool(re.search(r"\b(cheapest|lowest fee|cost|affordable|price|free|\$0)\b", prompt_lower))
    has_explicit_availability = bool(re.search(r"\b(earliest|soonest|available today|availability|available now)\b", prompt_lower))

    # Ambiguity check: if user asked for 'best' or 'top' without defining specific metric
    if has_ranking_keyword and not (has_explicit_satisfaction or has_explicit_success or has_explicit_distance or has_explicit_price or has_explicit_availability):
        spec_text = f" in **{specialty.value}**" if specialty and not is_negated else ""
        return IntentClassificationResult(
            intent=IntentType.AMBIGUOUS,
            confidence=0.95,
            filters=SearchFilters(specialty=specialty if not is_negated else None),
            normalized_entities=normalized_entities,
            negated_entities=negated_entities,
            ambiguity_detected=True,
            ambiguity_reason="Ambiguous 'best' ranking requested without defining the optimization metric.",
            clarification_options=[
                "⭐ Highest Patient Satisfaction",
                "📈 Highest Surgical Success Rate",
                "📍 Closest Distance",
                "💰 Lowest Consultation Fee",
                "📅 Earliest Availability"
            ],
            explanation=(
                f"⚠️ **Ambiguity Detected**: You asked for the 'best' doctor{spec_text}.\n\n"
                "Healthcare quality has multiple objective dimensions in our database. "
                "**What would you like to optimize for?**"
            ),
            raw_prompt=raw_prompt
        )

    # 10. General Ambiguous Inquiry ("Find me a doctor", "I need a doctor")
    if re.match(r"^(find\s+(?:me\s+)?a\s+doctor|i\s+need\s+a\s+doctor|show\s+doctors|get\s+doctor)$", prompt_lower):
        return IntentClassificationResult(
            intent=IntentType.AMBIGUOUS,
            confidence=0.9,
            ambiguity_detected=True,
            ambiguity_reason="No specialty or criteria specified.",
            clarification_options=[
                "🫀 Cardiology",
                "🧠 Neurology",
                "🦴 Orthopedics",
                "👶 Pediatrics",
                "🚨 Emergency"
            ],
            explanation="⚠️ **Specialty Required**: What medical specialty are you looking for?",
            raw_prompt=raw_prompt
        )

    # 11. Build SearchFilters & Intent
    filters = SearchFilters()

    if specialty and not is_negated:
        filters.specialty = specialty

    if "max_distance" in numeric_constraints:
        filters.max_distance = numeric_constraints["max_distance"]
    if "max_fee" in numeric_constraints:
        filters.max_fee = numeric_constraints["max_fee"]
    if "min_success_rate" in numeric_constraints:
        filters.min_success_rate = numeric_constraints["min_success_rate"]
    if "min_satisfaction" in numeric_constraints:
        filters.min_satisfaction = numeric_constraints["min_satisfaction"]
    if "available_today" in numeric_constraints:
        filters.available_today = numeric_constraints["available_today"]
    if "limit" in numeric_constraints:
        filters.limit = numeric_constraints["limit"]

    # Sorting & Intent Classification
    intent = IntentType.DOCTOR_SEARCH

    # Check Directory Intent
    is_directory = bool(re.search(r"\b(all|every|directory|complete list|full list)\b", prompt_lower))
    if is_directory and "limit" not in numeric_constraints:
        filters.limit = 200
        intent = IntentType.DIRECTORY

    # Check Affordability Intent
    is_cheap = bool(re.search(r"\b(cheap|cheapest|affordable|lowest fee|budget|low cost|free|\$0)\b", prompt_lower))
    is_cheap_negated = any("cheap" in neg or "affordable" in neg for neg in negated_phrases)

    if is_cheap and not is_cheap_negated:
        intent = IntentType.AFFORDABILITY
        filters.sort_by = SortMetric.CONSULTATION_FEE
        filters.sort_order = SortOrder.ASC

    # Check Distance Intent
    is_dist_query = bool(re.search(r"\b(nearest|closest|shortest distance|near me|nearby|how far|who is closest)\b", prompt_lower))
    if is_dist_query:
        intent = IntentType.DISTANCE
        filters.sort_by = SortMetric.DISTANCE_MILES
        filters.sort_order = SortOrder.ASC

    # Check Availability Intent
    is_avail_query = bool(re.search(r"\b(available today|available now|who is available|open today|see someone today)\b", prompt_lower))
    if is_avail_query and not is_dist_query and not is_cheap:
        intent = IntentType.AVAILABILITY
        filters.available_today = True
        filters.sort_by = SortMetric.NEXT_AVAILABLE_DATE
        filters.sort_order = SortOrder.ASC

    # Check Explicit Ranking
    if has_explicit_satisfaction:
        intent = IntentType.RANKING
        filters.sort_by = SortMetric.SATISFACTION_SCORE
        filters.sort_order = SortOrder.DESC
    elif has_explicit_success:
        intent = IntentType.RANKING
        filters.sort_by = SortMetric.SURGERY_SUCCESS_RATE
        filters.sort_order = SortOrder.DESC

    # Multi-constraint detection (e.g. specialty + distance + fee + availability)
    # If 3 or more constraints are explicitly requested together
    active_constraint_count = sum(1 for v in [filters.specialty, filters.max_distance, filters.max_fee, filters.min_success_rate, filters.min_satisfaction, filters.available_today] if v is not None)
    if active_constraint_count >= 3:
        intent = IntentType.DOCTOR_SEARCH

    return IntentClassificationResult(
        intent=intent,
        confidence=0.95,
        filters=filters,
        normalized_entities=normalized_entities,
        negated_entities=negated_entities,
        explanation=f"Parsed {intent.value} intent with {active_constraint_count} active database filter(s).",
        raw_prompt=raw_prompt
    )
