"""
DuckDB connection management.

IMPORTANT: the module-level ``duckdb.sql()`` / ``duckdb.execute()`` helpers operate
on a fresh in-memory database that does NOT contain the application tables.
Always connect to the file database through :func:`get_db_connection`.
"""
import duckdb as ddb

from app.core.config import get_settings


def get_db_connection() -> ddb.DuckDBPyConnection:
    """
    Open a connection to the persistent DuckDB database file.

    The parent directory is created if missing so the connection never fails
    on a fresh checkout. Callers are responsible for closing the connection
    (the ``get_db`` FastAPI dependency in ``app.api.deps`` does this for routes).
    """
    settings = get_settings()
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    return ddb.connect(str(settings.db_path))