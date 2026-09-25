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


@pytest.mark.parametrize("prompt,expected_max_price", [
    ("Find a 3BHK flat 60k", 60000),
    ("Apartment for 60 thousand in Indiranagar", 60000),
    ("3BHK flat 60K budget", 60000),
    ("Find a 3BHK flat under ₹60k", 60000),
    ("Flat in Koramangala 60 thousand rupees", 60000),
    ("Find a 3BHK flat under 60000 near top schools", 60000),
    ("Find a 3BHK flat in Koramangala under ₹60000", 60000),
    ("Find a 2BHK flat under ₹45,000", 45000),
    ("Gated community villa in Hyderabad under 1 lakh", 100000),
    ("Villa in Jubilee Hills Hyderabad under 1.5 lakh", 150000),
    ("Flat in Whitefield 50k/month", 50000),
    ("Apartment in Bandra for 75 thousand INR", 75000),
    ("Flat with 60000 rent", 60000),
])
def test_housing_price_parsing(prompt, expected_max_price):
    res = classify_intent_and_extract_entities(prompt)
    assert res.domain == DomainType.REAL_ESTATE
    assert res.housing_filters.max_price == expected_max_price


@pytest.mark.parametrize("prompt,expected_max_price", [
    ("Apartment near hospital within 1.5 miles", None),
    ("Safest neighborhood with low crime index < 20", None),
    ("House with school rating above 8 in Delhi NCR", None),
])
def test_housing_price_non_price_numerical_isolation(prompt, expected_max_price):
    res = classify_intent_and_extract_entities(prompt)
    assert res.domain == DomainType.REAL_ESTATE
    assert res.housing_filters.max_price == expected_max_price

