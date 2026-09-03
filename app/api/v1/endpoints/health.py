"""
Health / diagnostics endpoints.
"""
from fastapi import APIRouter, Depends
from duckdb import DuckDBPyConnection

from app.api.deps import get_db

router = APIRouter(tags=["health"])


@router.get("/test-db")
def test_database(conn: DuckDBPyConnection = Depends(get_db)):
    """List the tables available in the configured DuckDB database."""
    tables = conn.execute("SHOW TABLES").fetchall()
    return {"tables_found": [t[0] for t in tables]}