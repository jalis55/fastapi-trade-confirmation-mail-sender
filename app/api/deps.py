"""
Shared FastAPI dependencies.

``get_db`` provides a request-scoped DuckDB connection that is automatically
closed when the request finishes.
"""
from typing import Generator

from duckdb import DuckDBPyConnection

from app.db.connection import get_db_connection


def get_db() -> Generator[DuckDBPyConnection, None, None]:
    """Yield a DuckDB connection for the lifetime of the request."""
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()