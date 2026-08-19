"""
Pytest Suite for Parameterized Query Engine & SQL Sandbox
=========================================================
Tests SQL compilation safety, parameterized execution,
and SQL mutation blocklists (DROP, DELETE, UPDATE, INSERT, ALTER).
"""

import pytest
from models import SearchFilters, CanonicalSpecialty, SortOrder
from query_engine import build_safe_query, execute_query
from safety import validate_sql_sandbox_query


@pytest.mark.sql
def test_parameterized_query_building():
    filters = SearchFilters(
        specialty=CanonicalSpecialty.CARDIOLOGY,
        max_fee=1500,
        available_today=True
    )
    sql, params, applied = build_safe_query(filters)
    
    assert "specialty = ?" in sql
    assert "consultation_fee <= ?" in sql
    assert "is_available_today = 'Yes'" in sql
    assert params == ["Cardiology", 1500]


@pytest.mark.sql
def test_query_engine_execution():
    filters = SearchFilters(
        specialty=CanonicalSpecialty.CARDIOLOGY,
        limit=5
    )
    res = execute_query(filters)
    assert res.success is True
    assert res.row_count > 0
    assert len(res.data) > 0
    assert res.data[0]["specialty"] == "Cardiology"


@pytest.mark.sql
@pytest.mark.parametrize("safe_query", [
    "SELECT * FROM Doctors WHERE specialty = 'Cardiology' LIMIT 5;",
    "SELECT name, hospital_name, consultation_fee FROM Doctors WHERE consultation_fee < 1000;",
    "WITH TopDocs AS (SELECT * FROM Doctors WHERE satisfaction_score > 90) SELECT * FROM TopDocs;",
    "EXPLAIN QUERY PLAN SELECT * FROM Doctors WHERE city = 'Chennai';",
    "WITH x AS (SELECT 1) SELECT * FROM Doctors;",
    "SELECT * FROM Doctors /* inline comment */ WHERE 1=1;",
])
def test_sql_sandbox_allows_safe_selects(safe_query):
    is_safe, msg = validate_sql_sandbox_query(safe_query)
    assert is_safe is True, f"Expected safe for query: {safe_query}"


@pytest.mark.sql
@pytest.mark.parametrize("malicious_query", [
    "DROP TABLE Doctors;",
    "DELETE FROM Doctors WHERE id = 1;",
    "UPDATE Doctors SET consultation_fee = 0;",
    "INSERT INTO Doctors (name) VALUES ('Hacker');",
    "ALTER TABLE Doctors ADD COLUMN backdoor TEXT;",
    "PRAGMA table_info(Doctors);",
    "SELECT * FROM Doctors; DROP TABLE Doctors;",
    "SELECT * FROM sqlite_master;",
    "WITH x AS (SELECT 1) SELECT * FROM sqlite_master;",
    "WITH x AS (SELECT 1) SELECT * FROM RandomTable;",
    "WITH a AS (SELECT 1), b AS (SELECT * FROM RandomTable) SELECT * FROM a,b;",
    "SELECT * FROM Doctors AS d, RandomTable AS r;",
    "SELECT * FROM Doctors JOIN RandomTable ON Doctors.id = RandomTable.id;",
    "SELECT * FROM Doctors WHERE id IN (SELECT id FROM RandomTable);",
    "WITH RECURSIVE cnt(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM cnt) SELECT count(*) FROM cnt;",
    "SELECT name FROM pragma_table_info('Doctors');",
    "SELECT * FROM main.sqlite_master;",
    "SELECT * FROM RandomTable;",
    "WITH x AS (SELECT * FROM Doctors) SELECT * FROM x, RandomTable;",
])
def test_sql_sandbox_blocks_mutations_and_unauthorized_tables(malicious_query):
    is_safe, msg = validate_sql_sandbox_query(malicious_query)
    assert is_safe is False, f"Expected block for query: {malicious_query}"
