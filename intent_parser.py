"""
MedData AI & UrbanLocate - Multi-Domain Intent Classification & Entity Extraction Layer
Provides deterministic NLP parsing, synonym normalization, negation handling,
multi-constraint extraction, ambiguity interception, and multi-domain routing.
"""

import re
from typing import Dict, Any, List, Optional, Tuple

from models import (
    CanonicalSpecialty, SortMetric, SortOrder, IntentType, DomainType,
    SearchFilters, HousingSearchFilters, HousingSortMetric, PropertyType,
    IntentClassificationResult
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

HOUSING_DOMAIN_KEYWORDS = [
    r"\b(house|houses|home|homes|apartment|apartments|flat|flats|condo|condos|villa|villas|townhouse|townhome)\b",
    r"\b(rent|rental|bhk|bedrooms?|bathrooms?|sqft|neighborhood|crime|crime rate|school rating|schools?)\b",
    r"\b(livability|housing|property|properties|transit distance|safe neighborhood|best area)\b"
]

KNOWN_NEIGHBORHOODS = {
    "pacific heights": "Pacific Heights",
    "sunset district": "Sunset District",
    "sunset": "Sunset District",
    "mission valley": "Mission Valley",
    "mission": "Mission Valley",
    "silicon hills": "Silicon Hills",
    "silicon": "Silicon Hills",
    "downtown metro": "Downtown Metro",
    "downtown": "Downtown Metro",
    "marina bay": "Marina Bay",
    "marina": "Marina Bay",
    "green valley": "Green Valley",
    "beacon hill": "Beacon Hill",
    "highland park": "Highland Park"
}


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


def detect_domain(prompt: str, active_domain: Optional[DomainType] = None) -> DomainType:
    """Detects whether prompt is for Real Estate / Housing or Healthcare."""
    if active_domain == DomainType.REAL_ESTATE:
        return DomainType.REAL_ESTATE
    
    prompt_lower = prompt.lower()
    for kw in HOUSING_DOMAIN_KEYWORDS:
        if re.search(kw, prompt_lower):
            # If prompt mentions doctor/medical specifically, prioritize healthcare
            if not any(med in prompt_lower for med in ["cardiologist", "neurologist", "pediatrician", "orthopedic", "surgery", "doctor name"]):
                return DomainType.REAL_ESTATE

    return DomainType.HEALTHCARE


def parse_housing_constraints(prompt: str) -> HousingSearchFilters:
    """Extracts structured real estate constraints from natural language."""
    prompt_lower = prompt.lower()
    filters = HousingSearchFilters()

    # 1. Price extraction ($ or numbers)
    price_match = re.search(r"(?:under|less than|max|budget|below|up to|\$)\s*\$?(\d{3,5})", prompt_lower)
    if price_match:
        filters.max_price = int(price_match.group(1))

    # 2. Crime index extraction
    if re.search(r"\b(very safe|ultra safe|safest|lowest crime|minimal crime)\b", prompt_lower):
        filters.max_crime_index = 15
    elif re.search(r"\b(safe|low crime|less crime|safe area|low violence)\b", prompt_lower):
        filters.max_crime_index = 25
    elif re.search(r"(?:crime|crime index|crime score)\s*(?:<|under|less than|below|<=)\s*(\d{1,3})", prompt_lower):
        m = re.search(r"(?:crime|crime index|crime score)\s*(?:<|under|less than|below|<=)\s*(\d{1,3})", prompt_lower)
        filters.max_crime_index = int(m.group(1))

    # 3. School rating extraction
    if re.search(r"\b(top school|top schools|best school|best schools|elite schools|9\+ school)\b", prompt_lower):
        filters.min_school_rating = 9.0
    elif re.search(r"\b(good school|good schools|high rated schools?|great school)\b", prompt_lower):
        filters.min_school_rating = 8.0
    elif re.search(r"(?:school|schools|school rating)\s*(?:>|above|at least|min|>=)\s*(\d+(?:\.\d+)?)", prompt_lower):
        m = re.search(r"(?:school|schools|school rating)\s*(?:>|above|at least|min|>=)\s*(\d+(?:\.\d+)?)", prompt_lower)
        filters.min_school_rating = float(m.group(1))

    # 4. Hospital distance extraction
    hosp_match = re.search(r"(?:hospital|medical center|clinic)\s*(?:within|under|less than|<|below)\s*(\d+(?:\.\d+)?)\s*(?:mi|miles)?", prompt_lower)
    if hosp_match:
        filters.max_hospital_distance = float(hosp_match.group(1))
    elif re.search(r"\b(near hospital|close to hospital|hospital adjacent|nearby hospital)\b", prompt_lower):
        filters.max_hospital_distance = 1.5

    # 5. Transit distance extraction
    if re.search(r"\b(near transit|near metro|near subway|walkable|transit accessible)\b", prompt_lower):
        filters.max_transit_distance = 0.5

    # 6. Bedrooms (BHK / Bed)
    bhk_match = re.search(r"(\d+)\s*(?:bhk|bed|bedrooms?|br)\b", prompt_lower)
    if bhk_match:
        filters.min_bedrooms = int(bhk_match.group(1))

    # 7. Property Type
    if "villa" in prompt_lower:
        filters.property_type = PropertyType.VILLA
    elif "condo" in prompt_lower:
        filters.property_type = PropertyType.CONDO
    elif "townhouse" in prompt_lower or "townhome" in prompt_lower:
        filters.property_type = PropertyType.TOWNHOUSE
    elif "apartment" in prompt_lower or "flat" in prompt_lower:
        filters.property_type = PropertyType.APARTMENT
    elif "single family" in prompt_lower:
        filters.property_type = PropertyType.SINGLE_FAMILY

    # 8. Neighborhood
    for key, nbh_name in KNOWN_NEIGHBORHOODS.items():
        if key in prompt_lower:
            filters.neighborhood = nbh_name
            break

    # 9. Sorting
    if any(s in prompt_lower for s in ["cheapest", "lowest price", "affordable", "budget"]):
        filters.sort_by = HousingSortMetric.PRICE
        filters.sort_order = SortOrder.ASC
    elif any(s in prompt_lower for s in ["safest", "lowest crime", "least crime"]):
        filters.sort_by = HousingSortMetric.CRIME_INDEX
        filters.sort_order = SortOrder.ASC
    elif any(s in prompt_lower for s in ["best schools", "top schools", "highest rated schools"]):
        filters.sort_by = HousingSortMetric.SCHOOL_RATING
        filters.sort_order = SortOrder.DESC
    elif any(s in prompt_lower for s in ["closest to hospital", "nearest hospital"]):
        filters.sort_by = HousingSortMetric.HOSPITAL_DISTANCE
        filters.sort_order = SortOrder.ASC
    else:
        filters.sort_by = HousingSortMetric.LIVABILITY_SCORE
        filters.sort_order = SortOrder.DESC

    return filters


def classify_intent_and_extract_entities(prompt: str, active_domain: Optional[DomainType] = None) -> IntentClassificationResult:
    """
    Master multi-domain parser executing deterministic intent classification,
    safety guardrails, constraint extraction, and ambiguity handling.
    """
    domain = detect_domain(prompt, active_domain)

    # 1. Check prompt injection
    injection_check = check_prompt_injection(prompt)
    if injection_check:
        return IntentClassificationResult(
            domain=domain,
            intent=IntentType.PROMPT_INJECTION,
            safety_flags=["prompt_injection_blocked"],
            explanation=injection_check["message"],
            raw_prompt=prompt
        )

    # 2. If Real Estate domain, route to Housing Parser
    if domain == DomainType.REAL_ESTATE:
        housing_filters = parse_housing_constraints(prompt)
        return IntentClassificationResult(
            domain=DomainType.REAL_ESTATE,
            intent=IntentType.HOUSING_SEARCH,
            confidence=0.95,
            housing_filters=housing_filters,
            explanation="Deterministic Real Estate & Livability constraint extraction.",
            raw_prompt=prompt
        )

    # 3. Medical Safety & Clinical Advice Refusal Check
    advice_check = check_medical_advice_refusal(prompt)
    if advice_check:
        return IntentClassificationResult(
            domain=DomainType.HEALTHCARE,
            intent=IntentType.MEDICAL_ADVICE,
            safety_flags=["medical_advice_refusal"],
            explanation=advice_check["message"],
            raw_prompt=prompt
        )

    # 4. Acute Life-Threatening Emergency Interception
    emergency_check = check_acute_emergency(prompt)
    if emergency_check:
        return IntentClassificationResult(
            domain=DomainType.HEALTHCARE,
            intent=IntentType.EMERGENCY,
            safety_flags=["acute_emergency_detected"],
            explanation=emergency_check["message"],
            raw_prompt=prompt
        )

    # 5. Unknown Field Factuality Check
    unknown_check = check_unknown_attributes(prompt)
    if unknown_check:
        return IntentClassificationResult(
            domain=DomainType.HEALTHCARE,
            intent=IntentType.UNKNOWN_ATTRIBUTE,
            unknown_fields_requested=unknown_check["missing_fields"],
            explanation=unknown_check["message"],
            raw_prompt=prompt
        )

    # 6. Extract Negations
    negated_terms = extract_negations(prompt)

    # 7. Healthcare Specialty Matching
    prompt_lower = prompt.lower()
    matched_specialty: Optional[CanonicalSpecialty] = None
    for term, canonical in SPECIALTY_SYNONYMS.items():
        if re.search(r"\b" + re.escape(term) + r"\b", prompt_lower):
            if term not in " ".join(negated_terms):
                matched_specialty = canonical
                break

    # 8. Contradiction Detection
    contradictions = []
    if "free" in prompt_lower and ("$100" in prompt_lower or "$50" in prompt_lower or "$500" in prompt_lower or "expensive" in prompt_lower):
        contradictions.append("Query requests both Free ($0) and a positive fee threshold.")
    if re.search(r"\b(?:within|under|in|<|at)?\s*0\s*(?:mi|miles)\b", prompt_lower):
        contradictions.append("Search radius of 0 miles is impossible.")
    if "available today" in prompt_lower and "next week" in prompt_lower:
        contradictions.append("Query requests immediate same-day availability and next week.")

    if contradictions:
        return IntentClassificationResult(
            domain=DomainType.HEALTHCARE,
            intent=IntentType.CONTRADICTION,
            contradictions_detected=contradictions,
            explanation=f"⚠️ Contradictory filters detected: {'; '.join(contradictions)}",
            raw_prompt=prompt
        )

    # 9. Ambiguity Interception (Ranking vs Distance vs Cost)
    ambiguity_detected = False
    ambiguity_reason = None
    clarification_options = []
    
    if re.search(r"\b(best|top|recommended|highest rated)\b", prompt_lower):
        has_distance = bool(re.search(r"\b(near|close|distance|miles)\b", prompt_lower))
        has_price = bool(re.search(r"\b(cheap|cheapest|free|cost|fee|affordable)\b", prompt_lower))
        has_success = bool(re.search(r"\b(success|surgery|procedure|cure)\b", prompt_lower))
        has_satisfaction = bool(re.search(r"\b(patient rating|satisfaction|review)\b", prompt_lower))

        if not (has_distance or has_price or has_success or has_satisfaction):
            ambiguity_detected = True
            ambiguity_reason = "The term 'best' is ambiguous in healthcare discovery."
            clarification_options = [
                "Highest Patient Satisfaction Score (⭐)",
                "Highest Surgical Success Rate (📈)",
                "Closest Proximity / Distance (📍)",
                "Lowest Consultation Fee / Free ($)"
            ]

    # 10. Extract Numerical Constraints for Healthcare
    filters = SearchFilters()
    if matched_specialty:
        filters.specialty = matched_specialty

    # Max fee
    if "free" in prompt_lower:
        filters.max_fee = 0
    else:
        fee_match = re.search(r"(?:under|less than|fee|cost|below|\$)\s*\$?(\d{2,4})", prompt_lower)
        if fee_match:
            filters.max_fee = int(fee_match.group(1))

    # Max distance
    dist_match = re.search(r"(?:within|under|less than|<)\s*(\d+(?:\.\d+)?)\s*(?:mi|miles)", prompt_lower)
    if dist_match:
        filters.max_distance = float(dist_match.group(1))

    # Availability today
    if any(k in prompt_lower for k in ["available today", "today", "now", "same day", "open today"]):
        filters.available_today = True

    # Sorting
    if any(k in prompt_lower for k in ["closest", "nearest", "near me", "who is closest"]):
        filters.sort_by = SortMetric.DISTANCE_MILES
        filters.sort_order = SortOrder.ASC
    elif any(k in prompt_lower for k in ["cheapest", "lowest fee", "lowest cost", "affordable"]):
        filters.sort_by = SortMetric.CONSULTATION_FEE
        filters.sort_order = SortOrder.ASC
    elif any(k in prompt_lower for k in ["success rate", "highest success", "surgery success"]):
        filters.sort_by = SortMetric.SURGERY_SUCCESS_RATE
        filters.sort_order = SortOrder.DESC
    elif any(k in prompt_lower for k in ["satisfaction", "top rated", "highest satisfaction"]):
        filters.sort_by = SortMetric.SATISFACTION_SCORE
        filters.sort_order = SortOrder.DESC

    # Multi-constraint check
    active_constraints_count = sum([
        1 if filters.specialty else 0,
        1 if filters.max_fee is not None else 0,
        1 if filters.max_distance is not None else 0,
        1 if filters.available_today else 0
    ])

    # Determine intent type
    if ambiguity_detected:
        intent = IntentType.AMBIGUOUS
    elif any(d in prompt_lower for d in ["directory", "list all", "all doctors", "show database", "show all"]):
        intent = IntentType.DIRECTORY
        filters.limit = 200
    elif active_constraints_count >= 3:
        intent = IntentType.DOCTOR_SEARCH
    elif any(k in prompt_lower for k in ["closest", "nearest", "near me", "who is closest"]):
        intent = IntentType.DISTANCE
    elif any(k in prompt_lower for k in ["cheapest", "lowest fee", "lowest cost", "affordable", "free"]):
        intent = IntentType.AFFORDABILITY
    elif filters.available_today or "available" in prompt_lower:
        intent = IntentType.AVAILABILITY
    elif filters.sort_by:
        intent = IntentType.RANKING
    elif re.search(r"\b(hello|hi|hey|good morning)\b", prompt_lower):
        intent = IntentType.GREETING
    else:
        intent = IntentType.DOCTOR_SEARCH

    return IntentClassificationResult(
        domain=DomainType.HEALTHCARE,
        intent=intent,
        confidence=0.95,
        filters=filters,
        negated_entities=negated_terms,
        ambiguity_detected=ambiguity_detected,
        ambiguity_reason=ambiguity_reason,
        clarification_options=clarification_options,
        contradictions_detected=contradictions,
        explanation="Deterministic entity extraction and schema alignment.",
        raw_prompt=prompt
    )


# Backwards compatibility alias
parse_intent_and_filters = classify_intent_and_extract_entities
