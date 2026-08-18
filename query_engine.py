"""
MedData AI - Deterministic Query Engine Layer
Builds safe, parameterized SQL queries from validated SearchFilters, executes them,
measures execution time, and provides transparent zero-result relaxation options.
"""

import time
import sqlite3
from typing import Dict, Any, List, Tuple, Optional

from models import (
    SearchFilters, QueryResult, SortMetric, SortOrder,
    CanonicalSpecialty, DoctorRecord
)
from database import get_connection, DB_PATH

# Whitelist of allowed database columns to prevent any possibility of SQL injection
ALLOWED_COLUMNS = {
    "id", "name", "specialty", "primary_surgery", "surgery_success_rate",
    "satisfaction_score", "distance_miles", "consultation_fee",
    "is_available_today", "next_available_date"
}

ALLOWED_SORT_METRICS = {
    SortMetric.SATISFACTION_SCORE: "satisfaction_score",
    SortMetric.SURGERY_SUCCESS_RATE: "surgery_success_rate",
    SortMetric.DISTANCE_MILES: "distance_miles",
    SortMetric.CONSULTATION_FEE: "consultation_fee",
    SortMetric.NEXT_AVAILABLE_DATE: "next_available_date"
}


def build_safe_query(filters: SearchFilters) -> Tuple[str, List[Any], Dict[str, Any]]:
    """
    Constructs a safe, parameterized SQL query string and parameter list.
    Guarantees no arbitrary string concatenation of user input.
    """
    select_clause = """
        SELECT id, name, specialty, primary_surgery, surgery_success_rate,
               satisfaction_score, distance_miles, consultation_fee,
               is_available_today, next_available_date
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
        # Default deterministic ordering by distance ASC, satisfaction DESC
        order_clause = " ORDER BY distance_miles ASC, satisfaction_score DESC"
        applied_filters["sorted_by"] = "distance_miles (ASC), satisfaction_score (DESC) [Default]"

    # 9. LIMIT clause
    limit_clause = ""
    if filters.limit is not None and filters.limit > 0:
        limit_clause = " LIMIT ?"
        params.append(int(filters.limit))
        applied_filters["limit"] = filters.limit

    full_sql = (select_clause + full_where + order_clause + limit_clause).strip()
    return full_sql, params, applied_filters


def calculate_relaxation_suggestions(
    original_filters: SearchFilters, 
    conn: sqlite3.Connection
) -> List[Dict[str, Any]]:
    """
    When a multi-constraint search returns 0 results, this function tests
    what single constraint relaxations would yield matching doctors.
    Allows user-controlled relaxation without silent dropping of filters.
    """
    suggestions = []

    # 1. Test removing availability restriction
    if original_filters.available_today:
        test_filters = original_filters.model_copy()
        test_filters.available_today = None
        sql, params, _ = build_safe_query(test_filters)
        c = conn.cursor()
        c.execute(sql, params)
        count = len(c.fetchall())
        if count > 0:
            suggestions.append({
                "label": "📅 Remove Availability Restriction (Show all dates)",
                "action": "remove_availability",
                "result_count": count,
                "modified_filter": "available_today = None"
            })

    # 2. Test expanding distance
    if original_filters.max_distance is not None:
        expanded_dist = round(original_filters.max_distance * 2.5, 1)
        test_filters = original_filters.model_copy()
        test_filters.max_distance = expanded_dist
        sql, params, _ = build_safe_query(test_filters)
        c = conn.cursor()
        c.execute(sql, params)
        count = len(c.fetchall())
        if count > 0:
            suggestions.append({
                "label": f"📍 Expand Search Radius to {expanded_dist} miles",
                "action": "expand_distance",
                "new_distance": expanded_dist,
                "result_count": count,
                "modified_filter": f"max_distance = {expanded_dist}"
            })

    # 3. Test increasing max fee
    if original_filters.max_fee is not None:
        increased_fee = original_filters.max_fee + 150
        test_filters = original_filters.model_copy()
        test_filters.max_fee = increased_fee
        sql, params, _ = build_safe_query(test_filters)
        c = conn.cursor()
        c.execute(sql, params)
        count = len(c.fetchall())
        if count > 0:
            suggestions.append({
                "label": f"💰 Increase Maximum Fee to ${increased_fee}",
                "action": "increase_fee",
                "new_fee": increased_fee,
                "result_count": count,
                "modified_filter": f"max_fee = {increased_fee}"
            })

    # 4. Test lowering min success rate
    if original_filters.min_success_rate is not None and original_filters.min_success_rate > 90.0:
        test_filters = original_filters.model_copy()
        test_filters.min_success_rate = 88.0
        sql, params, _ = build_safe_query(test_filters)
        c = conn.cursor()
        c.execute(sql, params)
        count = len(c.fetchall())
        if count > 0:
            suggestions.append({
                "label": "📈 Relax Success Rate Requirement to ≥ 88%",
                "action": "lower_success_rate",
                "new_rate": 88.0,
                "result_count": count,
                "modified_filter": "min_success_rate = 88.0%"
            })

    return suggestions


def execute_doctor_search(
    filters: SearchFilters, 
    conn: Optional[sqlite3.Connection] = None,
    db_path: str = DB_PATH
) -> QueryResult:
    """
    Executes a deterministic doctor search with strict parameterization and metrics.
    """
    should_close = False
    if conn is None:
        conn = get_connection(db_path)
        should_close = True

    try:
        sql, params, applied_filters = build_safe_query(filters)
        
        start_time = time.perf_counter()
        c = conn.cursor()
        c.execute(sql, params)
        rows = c.fetchall()
        exec_time_ms = round((time.perf_counter() - start_time) * 1000, 2)

        data = [dict(row) for row in rows]
        row_count = len(data)

        # Generate clear explanation of filtering logic
        explanation_parts = []
        if applied_filters.get("specialty"):
            explanation_parts.append(f"Specialty = '{applied_filters['specialty']}'")
        if applied_filters.get("max_distance"):
            explanation_parts.append(f"Distance ≤ {applied_filters['max_distance']}")
        if applied_filters.get("max_fee"):
            explanation_parts.append(f"Fee ≤ {applied_filters['max_fee']}")
        if applied_filters.get("available_today"):
            explanation_parts.append("Available Today = 'Yes'")
        if applied_filters.get("min_satisfaction"):
            explanation_parts.append(f"Satisfaction ≥ {applied_filters['min_satisfaction']}")
        if applied_filters.get("min_success_rate"):
            explanation_parts.append(f"Success Rate ≥ {applied_filters['min_success_rate']}")

        filter_summary = ", ".join(explanation_parts) if explanation_parts else "All doctors (no filters)"
        sort_summary = applied_filters.get("sorted_by", "default")
        limit_summary = applied_filters.get("limit", "unlimited")

        explanation = f"Queried Doctors table ({filter_summary}), sorted by {sort_summary}, limit {limit_summary}."

        relaxation_suggestions = []
        if row_count == 0:
            relaxation_suggestions = calculate_relaxation_suggestions(filters, conn)

        return QueryResult(
            success=True,
            data=data,
            row_count=row_count,
            sql_template=sql,
            params=params,
            execution_time_ms=exec_time_ms,
            applied_filters=applied_filters,
            explanation=explanation,
            relaxation_suggestions=relaxation_suggestions
        )

    except Exception as e:
        return QueryResult(
            success=False,
            error_message=f"Database execution error: {str(e)}",
            data=[],
            row_count=0,
            execution_time_ms=0.0
        )
    finally:
        if should_close:
            conn.close()


def get_doctor_details_by_id(doctor_id: int, db_path: str = DB_PATH) -> Optional[Dict[str, Any]]:
    """Retrieves full verified database record for a single doctor by ID."""
    conn = get_connection(db_path)
    c = conn.cursor()
    c.execute("""
        SELECT id, name, specialty, primary_surgery, surgery_success_rate,
               satisfaction_score, distance_miles, consultation_fee,
               is_available_today, next_available_date
        FROM Doctors
        WHERE id = ?
    """, (doctor_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None
