"""
MedData AI & UrbanLocate - Multi-Domain Deterministic Query Engine Layer
Builds safe, parameterized SQL queries from validated filters, executes them,
measures latency, and provides transparent zero-result relaxation options.
"""

import time
import sqlite3
from typing import Dict, Any, List, Tuple, Optional

from models import (
    SearchFilters, HousingSearchFilters, QueryResult, SortMetric, SortOrder,
    HousingSortMetric, DomainType, CanonicalSpecialty
)
from database import get_connection, DB_PATH

# Whitelist of allowed database columns to prevent SQL injection
ALLOWED_DOCTOR_COLUMNS = {
    "id", "name", "specialty", "primary_surgery", "surgery_success_rate",
    "satisfaction_score", "distance_miles", "consultation_fee",
    "is_available_today", "next_available_date", "latitude", "longitude"
}

ALLOWED_HOUSING_COLUMNS = {
    "id", "title", "neighborhood", "property_type", "price_per_month",
    "bedrooms", "bathrooms", "sqft", "crime_index_score", "school_rating",
    "hospital_dist_miles", "transit_dist_miles", "market_dist_miles",
    "livability_score", "latitude", "longitude"
}

ALLOWED_SORT_METRICS = {
    SortMetric.SATISFACTION_SCORE: "satisfaction_score",
    SortMetric.SURGERY_SUCCESS_RATE: "surgery_success_rate",
    SortMetric.DISTANCE_MILES: "distance_miles",
    SortMetric.CONSULTATION_FEE: "consultation_fee",
    SortMetric.NEXT_AVAILABLE_DATE: "next_available_date"
}

ALLOWED_HOUSING_SORT_METRICS = {
    HousingSortMetric.LIVABILITY_SCORE: "livability_score",
    HousingSortMetric.PRICE: "price_per_month",
    HousingSortMetric.CRIME_INDEX: "crime_index_score",
    HousingSortMetric.SCHOOL_RATING: "school_rating",
    HousingSortMetric.HOSPITAL_DISTANCE: "hospital_dist_miles",
    HousingSortMetric.TRANSIT_DISTANCE: "transit_dist_miles"
}


# ==========================================
# 🏥 HEALTHCARE QUERY BUILDER
# ==========================================

def build_safe_query(filters: SearchFilters) -> Tuple[str, List[Any], Dict[str, Any]]:
    """
    Constructs a safe, parameterized SQL query for Doctors table.
    Guarantees no arbitrary string concatenation of user input.
    """
    select_clause = """
        SELECT id, name, specialty, primary_surgery, surgery_success_rate,
               satisfaction_score, distance_miles, consultation_fee,
               is_available_today, next_available_date, latitude, longitude
        FROM Doctors
    """
    where_clauses = []
    params: List[Any] = []
    applied_filters: Dict[str, Any] = {}

    # 1. Specialty filter (whitelist validated via CanonicalSpecialty Enum)
    if filters.specialty:
        where_clauses.append("specialty = ?")
        params.append(filters.specialty.value)
        applied_filters["specialty"] = filters.specialty.value

    # 2. Doctor Name filter
    if filters.doctor_name:
        where_clauses.append("name LIKE ?")
        params.append(f"%{filters.doctor_name}%")
        applied_filters["doctor_name"] = filters.doctor_name

    # 3. Max Distance
    if filters.max_distance is not None:
        where_clauses.append("distance_miles <= ?")
        params.append(float(filters.max_distance))
        applied_filters["max_distance"] = f"{filters.max_distance} miles"

    # 4. Max Consultation Fee
    if filters.max_fee is not None:
        where_clauses.append("consultation_fee <= ?")
        params.append(int(filters.max_fee))
        applied_filters["max_fee"] = f"${filters.max_fee}"

    # 5. Min Patient Satisfaction Score
    if filters.min_satisfaction is not None:
        where_clauses.append("satisfaction_score >= ?")
        params.append(int(filters.min_satisfaction))
        applied_filters["min_satisfaction"] = f"{filters.min_satisfaction}/100"

    # 6. Min Surgical Success Rate
    if filters.min_success_rate is not None:
        where_clauses.append("surgery_success_rate >= ?")
        params.append(float(filters.min_success_rate))
        applied_filters["min_success_rate"] = f"{filters.min_success_rate}%"

    # 7. Available Today
    if filters.available_today is True:
        where_clauses.append("is_available_today = 'Yes'")
        applied_filters["available_today"] = "Yes"

    # Assemble WHERE clause
    full_where = ""
    if where_clauses:
        full_where = " WHERE " + " AND ".join(where_clauses)

    # 8. ORDER BY clause (Strict whitelist)
    order_clause = ""
    if filters.sort_by and filters.sort_by in ALLOWED_SORT_METRICS:
        column_name = ALLOWED_SORT_METRICS[filters.sort_by]
        direction = "DESC" if filters.sort_order == SortOrder.DESC else "ASC"
        order_clause = f" ORDER BY {column_name} {direction}"
        applied_filters["sorted_by"] = f"{column_name} ({direction})"
    else:
        order_clause = " ORDER BY distance_miles ASC, satisfaction_score DESC"

    # 9. LIMIT clause
    limit_clause = f" LIMIT {filters.limit}"

    sql_template = select_clause + full_where + order_clause + limit_clause
    return sql_template.strip(), params, applied_filters


def execute_doctor_search(filters: SearchFilters, db_path: str = DB_PATH) -> QueryResult:
    """Executes a safe parameterized doctor query and returns QueryResult."""
    start_time = time.perf_counter()
    sql_template, params, applied_filters = build_safe_query(filters)

    try:
        conn = get_connection(db_path)
        c = conn.cursor()
        c.execute(sql_template, params)
        rows = [dict(row) for row in c.fetchall()]
        conn.close()
        
        execution_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
        row_count = len(rows)

        relaxation_suggestions = []
        if row_count == 0:
            relaxation_suggestions = generate_relaxation_suggestions(filters, db_path)

        explanation = f"Found {row_count} verified doctor(s) matching your constraints."
        if row_count == 0:
            explanation = "No doctors in the database currently match all specified filters."

        return QueryResult(
            success=True,
            domain=DomainType.HEALTHCARE,
            data=rows,
            row_count=row_count,
            sql_template=sql_template,
            params=params,
            execution_time_ms=execution_time_ms,
            applied_filters=applied_filters,
            explanation=explanation,
            relaxation_suggestions=relaxation_suggestions
        )
    except Exception as e:
        execution_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return QueryResult(
            success=False,
            domain=DomainType.HEALTHCARE,
            data=[],
            row_count=0,
            sql_template=sql_template,
            params=params,
            execution_time_ms=execution_time_ms,
            applied_filters=applied_filters,
            explanation="Failed to execute database query safely.",
            error_message=str(e)
        )


# ==========================================
# 🏡 REAL ESTATE & HOUSING QUERY BUILDER
# ==========================================

def build_safe_housing_query(filters: HousingSearchFilters) -> Tuple[str, List[Any], Dict[str, Any]]:
    """Constructs safe parameterized SQL for the Properties table."""
    select_clause = """
        SELECT id, title, neighborhood, property_type, price_per_month,
               bedrooms, bathrooms, sqft, crime_index_score, school_rating,
               hospital_dist_miles, transit_dist_miles, market_dist_miles,
               livability_score, latitude, longitude
        FROM Properties
    """
    where_clauses = []
    params: List[Any] = []
    applied_filters: Dict[str, Any] = {}

    if filters.city:
        where_clauses.append("city = ?")
        params.append(filters.city)
        applied_filters["city"] = filters.city

    if filters.neighborhood:
        where_clauses.append("neighborhood = ?")
        params.append(filters.neighborhood)
        applied_filters["neighborhood"] = filters.neighborhood

    if filters.property_type:
        where_clauses.append("property_type = ?")
        params.append(filters.property_type.value)
        applied_filters["property_type"] = filters.property_type.value

    if filters.max_price is not None:
        where_clauses.append("price_per_month <= ?")
        params.append(int(filters.max_price))
        applied_filters["max_price"] = f"${filters.max_price}/mo"

    if filters.max_crime_index is not None:
        where_clauses.append("crime_index_score <= ?")
        params.append(int(filters.max_crime_index))
        applied_filters["max_crime_index"] = f"<= {filters.max_crime_index} (Safe)"

    if filters.min_school_rating is not None:
        where_clauses.append("school_rating >= ?")
        params.append(float(filters.min_school_rating))
        applied_filters["min_school_rating"] = f">= {filters.min_school_rating}/10"

    if filters.max_hospital_distance is not None:
        where_clauses.append("hospital_dist_miles <= ?")
        params.append(float(filters.max_hospital_distance))
        applied_filters["max_hospital_distance"] = f"<= {filters.max_hospital_distance} mi"

    if filters.max_transit_distance is not None:
        where_clauses.append("transit_dist_miles <= ?")
        params.append(float(filters.max_transit_distance))
        applied_filters["max_transit_distance"] = f"<= {filters.max_transit_distance} mi"

    if filters.min_bedrooms is not None:
        where_clauses.append("bedrooms >= ?")
        params.append(int(filters.min_bedrooms))
        applied_filters["min_bedrooms"] = f"{filters.min_bedrooms}+ BHK"

    if filters.min_livability_score is not None:
        where_clauses.append("livability_score >= ?")
        params.append(int(filters.min_livability_score))
        applied_filters["min_livability_score"] = f"{filters.min_livability_score}/100"

    full_where = ""
    if where_clauses:
        full_where = " WHERE " + " AND ".join(where_clauses)

    order_clause = " ORDER BY livability_score DESC, price_per_month ASC"
    if filters.sort_by and filters.sort_by in ALLOWED_HOUSING_SORT_METRICS:
        column_name = ALLOWED_HOUSING_SORT_METRICS[filters.sort_by]
        direction = "DESC" if filters.sort_order == SortOrder.DESC else "ASC"
        order_clause = f" ORDER BY {column_name} {direction}"
        applied_filters["sorted_by"] = f"{column_name} ({direction})"

    limit_clause = f" LIMIT {filters.limit}"

    sql_template = select_clause + full_where + order_clause + limit_clause
    return sql_template.strip(), params, applied_filters


def execute_housing_search(filters: HousingSearchFilters, db_path: str = DB_PATH) -> QueryResult:
    """Executes a safe parameterized housing search."""
    start_time = time.perf_counter()
    sql_template, params, applied_filters = build_safe_housing_query(filters)

    try:
        conn = get_connection(db_path)
        c = conn.cursor()
        c.execute(sql_template, params)
        rows = [dict(row) for row in c.fetchall()]
        conn.close()
        
        execution_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
        row_count = len(rows)

        relaxation_suggestions = []
        if row_count == 0:
            relaxation_suggestions = [
                {"description": "Increase budget threshold by $500", "relaxed_filter": "max_price"},
                {"description": "Expand hospital search radius by +2.0 miles", "relaxed_filter": "max_hospital_distance"},
                {"description": "Permit moderate crime index up to 40", "relaxed_filter": "max_crime_index"}
            ]

        explanation = f"Found {row_count} verified property record(s) matching your livability criteria."
        if row_count == 0:
            explanation = "No properties in the database currently match all specified housing filters."

        return QueryResult(
            success=True,
            domain=DomainType.REAL_ESTATE,
            data=rows,
            row_count=row_count,
            sql_template=sql_template,
            params=params,
            execution_time_ms=execution_time_ms,
            applied_filters=applied_filters,
            explanation=explanation,
            relaxation_suggestions=relaxation_suggestions
        )
    except Exception as e:
        execution_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return QueryResult(
            success=False,
            domain=DomainType.REAL_ESTATE,
            data=[],
            row_count=0,
            sql_template=sql_template,
            params=params,
            execution_time_ms=execution_time_ms,
            applied_filters=applied_filters,
            explanation="Failed to execute housing database query safely.",
            error_message=str(e)
        )


def generate_relaxation_suggestions(filters: SearchFilters, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """Calculates specific relaxed filters that will produce non-zero doctor results."""
    suggestions = []
    
    # 1. Relax distance
    if filters.max_distance is not None:
        relaxed_distance = filters.max_distance + 10.0
        relaxed_filters = filters.model_copy(update={"max_distance": relaxed_distance})
        sql, params, _ = build_safe_query(relaxed_filters)
        conn = get_connection(db_path)
        c = conn.cursor()
        c.execute(sql, params)
        cnt = len(c.fetchall())
        conn.close()
        if cnt > 0:
            suggestions.append({
                "description": f"Expand search radius to {relaxed_distance} miles (Yields {cnt} doctors)",
                "relaxed_filter": "max_distance",
                "new_value": relaxed_distance
            })

    # 2. Relax fee
    if filters.max_fee is not None:
        relaxed_fee = filters.max_fee + 100
        relaxed_filters = filters.model_copy(update={"max_fee": relaxed_fee})
        sql, params, _ = build_safe_query(relaxed_filters)
        conn = get_connection(db_path)
        c = conn.cursor()
        c.execute(sql, params)
        cnt = len(c.fetchall())
        conn.close()
        if cnt > 0:
            suggestions.append({
                "description": f"Increase max fee to ${relaxed_fee} (Yields {cnt} doctors)",
                "relaxed_filter": "max_fee",
                "new_value": relaxed_fee
            })

    # 3. Relax same-day availability
    if filters.available_today:
        relaxed_filters = filters.model_copy(update={"available_today": None})
        sql, params, _ = build_safe_query(relaxed_filters)
        conn = get_connection(db_path)
        c = conn.cursor()
        c.execute(sql, params)
        cnt = len(c.fetchall())
        conn.close()
        if cnt > 0:
            suggestions.append({
                "description": f"Include doctors available later this week (Yields {cnt} doctors)",
                "relaxed_filter": "available_today",
                "new_value": None
            })

    return suggestions

# Standard alias
execute_query = execute_doctor_search
