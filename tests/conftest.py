"""
MedData AI -- Pytest Fixtures & Configuration
=============================================
Provides clean test database fixtures, mock clients, and execution markers.
"""

import os
import pytest
import sqlite3
from pathlib import Path
from database import initialize_database, get_db_connection


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Ensure database tables and seed data are initialized."""
    initialize_database()
    yield


@pytest.fixture
def db_conn():
    """Yields a clean database connection."""
    conn = get_db_connection()
    yield conn
    conn.close()


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "safety: clinical and injection safety tests")
    config.addinivalue_line("markers", "sql: SQL sandbox and compilation tests")
    config.addinivalue_line("markers", "api: FastAPI REST API integration tests")
    config.addinivalue_line("markers", "benchmark: statistical evaluation benchmark")
