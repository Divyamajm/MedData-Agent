"""
Pytest Suite for Intent Parser & Entity Normalization
=====================================================
Validates natural language intent routing, specialty synonym resolution,
negation extraction, and multi-constraint parsing.
"""

import pytest
from models import IntentType, CanonicalSpecialty, DomainType
from intent_parser import (
    classify_intent_and_extract_entities,
    detect_domain,
    parse_user_intent_hybrid
)


@pytest.mark.parametrize("prompt,expected_spec", [
    ("Find a cardiologist in Chennai", CanonicalSpecialty.CARDIOLOGY),
    ("Top neurologists nearby", CanonicalSpecialty.NEUROLOGY),
    ("Need an orthopedic surgeon", CanonicalSpecialty.ORTHOPEDICS),
    ("Pediatrician available today", CanonicalSpecialty.PEDIATRICS),
])
def test_specialty_synonym_normalization(prompt, expected_spec):
    res = classify_intent_and_extract_entities(prompt)
    assert res.filters.specialty == expected_spec


@pytest.mark.parametrize("prompt,expected_intent", [
    ("Show all doctors", IntentType.DIRECTORY),
    ("Who is the best cardiologist?", IntentType.AMBIGUOUS),
    ("Nearest doctor", IntentType.DISTANCE),
    ("Cheapest cardiologist under 1000", IntentType.AFFORDABILITY),
    ("Doctor available today", IntentType.AVAILABILITY),
])
def test_intent_classification_routing(prompt, expected_intent):
    res = classify_intent_and_extract_entities(prompt)
    assert res.intent == expected_intent


def test_negation_extraction():
    res = classify_intent_and_extract_entities("I don't need a cardiologist")
    assert any("cardio" in n.lower() for n in res.negated_entities)


def test_multi_constraint_extraction():
    res = classify_intent_and_extract_entities("Find a cardiologist within 5 miles under 1500 available today")
    assert res.filters.specialty == CanonicalSpecialty.CARDIOLOGY
    assert res.filters.max_fee == 1500
    assert res.filters.available_today is True


def test_domain_detection():
    assert detect_domain("Find a 3BHK flat in Koramangala") == DomainType.REAL_ESTATE
    assert detect_domain("Find a cardiologist in Apollo hospital") == DomainType.HEALTHCARE


def test_hybrid_parser_deterministic_mode():
    res, engine, latency = parse_user_intent_hybrid("Find a cardiologist in Chennai under 1500", engine="deterministic")
    assert res.filters.specialty == CanonicalSpecialty.CARDIOLOGY
    assert res.filters.max_fee == 1500
    assert "Deterministic" in engine
    assert latency < 25.0
