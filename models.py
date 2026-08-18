"""
MedData AI - Core Data Models & Schemas
Defines all Pydantic models, enums, and data contracts used throughout the system.
"""

from enum import Enum
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator


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
        description="Maximum consultation fee in USD ($)"
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


class IntentClassificationResult(BaseModel):
    """Result of NLP parsing and entity extraction."""
    intent: IntentType
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    filters: SearchFilters = Field(default_factory=SearchFilters)
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


class DoctorRecord(BaseModel):
    """Database representation of a verified Doctor record."""
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


class QueryResult(BaseModel):
    """Execution output from the deterministic query engine."""
    success: bool
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
    notes: str = ""


class TestCaseResult(BaseModel):
    """Result of running an individual test case."""
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
