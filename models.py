"""
MedData AI & UrbanLocate - Multi-Domain Core Data Models & Schemas
Defines all Pydantic models, enums, and data contracts used across Healthcare and Real Estate engines.
"""

from enum import Enum
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator


class DomainType(str, Enum):
    """Active data domain in the discovery platform."""
    HEALTHCARE = "healthcare"
    REAL_ESTATE = "real_estate"
    DYNAMIC_DATASET = "dynamic_dataset"


# ==========================================
# 🏥 HEALTHCARE DOMAIN MODELS & ENUMS
# ==========================================

class CanonicalSpecialty(str, Enum):
    """Supported medical specialties in the database."""
    CARDIOLOGY = "Cardiology"
    NEUROLOGY = "Neurology"
    ORTHOPEDICS = "Orthopedics"
    PEDIATRICS = "Pediatrics"
    EMERGENCY = "Emergency"


class SortMetric(str, Enum):
    """Allowed database columns for sorting doctor results."""
    SATISFACTION_SCORE = "satisfaction_score"
    SURGERY_SUCCESS_RATE = "surgery_success_rate"
    DISTANCE_MILES = "distance_miles"
    CONSULTATION_FEE = "consultation_fee"
    NEXT_AVAILABLE_DATE = "next_available_date"


class SortOrder(str, Enum):
    """Allowed sort directions."""
    ASC = "ASC"
    DESC = "DESC"


class IntentType(str, Enum):
    """Supported user query intent categories."""
    EMERGENCY = "emergency"
    DOCTOR_SEARCH = "doctor_search"
    SPECIALTY_SEARCH = "specialty_search"
    AFFORDABILITY = "affordability"
    DISTANCE = "distance"
    AVAILABILITY = "availability"
    DIRECTORY = "directory"
    RANKING = "ranking"
    DOCTOR_DETAILS = "doctor_details"
    COMPARISON = "comparison"
    APPOINTMENT_REQUEST = "appointment_request"
    GREETING = "greeting"
    MEDICAL_ADVICE = "medical_advice"
    UNKNOWN_ATTRIBUTE = "unknown_attribute"
    CONTRADICTION = "contradiction"
    AMBIGUOUS = "ambiguous"
    PROMPT_INJECTION = "prompt_injection"
    HOUSING_SEARCH = "housing_search"
    DYNAMIC_SEARCH = "dynamic_search"
    UNSUPPORTED = "unsupported"


class SearchFilters(BaseModel):
    """Deterministic, validated filter set for querying the Doctors table."""
    specialty: Optional[CanonicalSpecialty] = Field(
        default=None, 
        description="Canonical specialty filter"
    )
    min_satisfaction: Optional[int] = Field(
        default=None, 
        ge=0, 
        le=100, 
        description="Minimum patient satisfaction score (0-100)"
    )
    min_success_rate: Optional[float] = Field(
        default=None, 
        ge=0.0, 
        le=100.0, 
        description="Minimum surgical success rate percentage (0-100)"
    )
    max_distance: Optional[float] = Field(
        default=None, 
        ge=0.0, 
        description="Maximum distance in miles"
    )
    max_fee: Optional[int] = Field(
        default=None, 
        ge=0, 
        description="Maximum consultation fee in INR (₹)"
    )
    available_today: Optional[bool] = Field(
        default=None, 
        description="Whether doctor must be available today ('Yes')"
    )
    doctor_name: Optional[str] = Field(
        default=None, 
        description="Specific doctor name search substring"
    )
    sort_by: Optional[SortMetric] = Field(
        default=None, 
        description="Column name to sort results by"
    )
    sort_order: Optional[SortOrder] = Field(
        default=SortOrder.ASC, 
        description="Sort direction (ASC or DESC)"
    )
    limit: Optional[int] = Field(
        default=5, 
        ge=1, 
        le=200, 
        description="Maximum number of rows to return"
    )

    @field_validator("max_distance")
    @classmethod
    def validate_distance(cls, v):
        if v is not None and v < 0:
            raise ValueError("Distance cannot be negative")
        return v


class DoctorRecord(BaseModel):
    """Database representation of a Doctor specialist record with geo-coordinates."""
    id: int
    name: str
    specialty: str
    primary_surgery: str
    surgery_success_rate: float
    satisfaction_score: int
    distance_miles: float
    consultation_fee: int
    is_available_today: str
    next_available_date: str
    latitude: Optional[float] = 37.7749
    longitude: Optional[float] = -122.4194


# ==========================================
# 🏡 REAL ESTATE & HOUSING DOMAIN MODELS
# ==========================================

class PropertyType(str, Enum):
    """Supported property architectural types."""
    APARTMENT = "Apartment"
    CONDO = "Condo"
    TOWNHOUSE = "Townhouse"
    SINGLE_FAMILY = "Single Family"
    VILLA = "Luxury Villa"


class HousingSortMetric(str, Enum):
    """Columns for sorting real estate results."""
    LIVABILITY_SCORE = "livability_score"
    PRICE = "price_per_month"
    CRIME_INDEX = "crime_index_score"
    SCHOOL_RATING = "school_rating"
    HOSPITAL_DISTANCE = "hospital_dist_miles"
    TRANSIT_DISTANCE = "transit_dist_miles"


class HousingSearchFilters(BaseModel):
    """Validated filter set for querying the Properties / Housing table."""
    city: Optional[str] = Field(default=None, description="City name filter (e.g. Bengaluru, Mumbai, Delhi-NCR, Hyderabad, Chennai)")
    neighborhood: Optional[str] = Field(default=None, description="Neighborhood name filter")
    property_type: Optional[PropertyType] = Field(default=None, description="Property type")
    max_price: Optional[int] = Field(default=None, ge=0, description="Max monthly rent or price in INR (₹)")
    max_crime_index: Optional[int] = Field(default=None, ge=0, le=100, description="Max crime index (0-100, lower is safer)")
    min_school_rating: Optional[float] = Field(default=None, ge=1.0, le=10.0, description="Min school rating (1-10)")
    max_hospital_distance: Optional[float] = Field(default=None, ge=0.0, description="Max distance to nearest hospital in km")
    max_transit_distance: Optional[float] = Field(default=None, ge=0.0, description="Max distance to public transit in km")
    min_bedrooms: Optional[int] = Field(default=None, ge=1, le=10, description="Minimum number of bedrooms")
    min_livability_score: Optional[int] = Field(default=None, ge=0, le=100, description="Minimum overall composite livability score")
    sort_by: Optional[HousingSortMetric] = Field(default=HousingSortMetric.LIVABILITY_SCORE, description="Sort column")
    sort_order: Optional[SortOrder] = Field(default=SortOrder.DESC, description="Sort direction")
    limit: Optional[int] = Field(default=5, ge=1, le=100, description="Max rows to return")


class PropertyRecord(BaseModel):
    """Database representation of a verified property / neighborhood record."""
    id: int
    title: str
    city: str = "Bengaluru"
    neighborhood: str
    property_type: str
    price_per_month: int
    bedrooms: int
    bathrooms: float
    sqft: int
    crime_index_score: int          # 0-100 (lower is safer)
    school_rating: float            # 1.0 - 10.0 (higher is better)
    hospital_dist_miles: float      # distance in km
    transit_dist_miles: float       # distance in km
    market_dist_miles: float        # distance to shopping/grocery
    livability_score: int           # Computed 0-100 composite score
    latitude: float
    longitude: float


# ==========================================
# 📅 APPOINTMENT SCHEDULER & BOOKING MODELS
# ==========================================

class AppointmentBookingRequest(BaseModel):
    """Validated patient appointment booking payload."""
    doctor_id: int
    doctor_name: str
    specialty: str
    patient_name: str
    patient_email: str
    appointment_date: str           # YYYY-MM-DD
    time_slot: str                  # e.g. "09:00 AM", "02:00 PM"
    symptoms_reason: str = "General Consultation"


class AppointmentRecord(BaseModel):
    """Stored appointment in database."""
    id: int
    doctor_id: int
    doctor_name: str
    specialty: str
    patient_name: str
    patient_email: str
    appointment_date: str
    time_slot: str
    symptoms_reason: str
    created_at: str
    status: str = "CONFIRMED"


# ==========================================
# 🧠 INTENT & EXPLAINABILITY AUDIT MODELS
# ==========================================

class IntentClassificationResult(BaseModel):
    """Result of NLP parsing and entity extraction."""
    domain: DomainType = DomainType.HEALTHCARE
    intent: IntentType
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    filters: SearchFilters = Field(default_factory=SearchFilters)
    housing_filters: Optional[HousingSearchFilters] = None
    normalized_entities: Dict[str, Any] = Field(default_factory=dict)
    negated_entities: List[str] = Field(default_factory=list)
    ambiguity_detected: bool = False
    ambiguity_reason: Optional[str] = None
    clarification_options: List[str] = Field(default_factory=list)
    contradictions_detected: List[str] = Field(default_factory=list)
    unknown_fields_requested: List[str] = Field(default_factory=list)
    safety_flags: List[str] = Field(default_factory=list)
    explanation: str = ""
    raw_prompt: str = ""


class QueryResult(BaseModel):
    """Execution output from the deterministic query engine."""
    success: bool
    domain: DomainType = DomainType.HEALTHCARE
    data: List[Dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    sql_template: str = ""
    params: List[Any] = Field(default_factory=list)
    execution_time_ms: float = 0.0
    applied_filters: Dict[str, Any] = Field(default_factory=dict)
    explanation: str = ""
    error_message: Optional[str] = None
    relaxation_suggestions: List[Dict[str, Any]] = Field(default_factory=list)


class ExplainabilityAudit(BaseModel):
    """Complete audit record for user-facing explainability panels."""
    raw_query: str
    domain: str
    intent: str
    confidence: float
    interpreted_entities: Dict[str, Any]
    negated_entities: List[str]
    applied_filters: Dict[str, Any]
    sql_query: str
    sql_parameters: List[Any]
    execution_time_ms: float
    result_count: int
    rationale: str
    database_grounded: bool = True
    ai_fabrication_check: str = "PASSED - All values sourced directly from SQLite rows."


class TestCase(BaseModel):
    """Automated test case definition."""
    __test__ = False
    id: str
    category: str
    description: str
    input_prompt: str
    expected_intent: IntentType
    expected_ambiguity: bool = False
    expected_specialty: Optional[CanonicalSpecialty] = None
    expected_safety_refusal: bool = False
    expected_unknown_attribute: bool = False
    expected_contradiction: bool = False
    expected_min_results: int = 0
    expected_domain: DomainType = DomainType.HEALTHCARE
    notes: str = ""


class TestCaseResult(BaseModel):
    """Result of running an individual test case."""
    __test__ = False
    test_case: TestCase
    actual_intent: IntentType
    actual_ambiguity: bool
    actual_specialty: Optional[str]
    actual_sql: str
    actual_params: List[Any]
    result_count: int
    passed: bool
    failure_reasons: List[str] = Field(default_factory=list)
    execution_time_ms: float = 0.0
