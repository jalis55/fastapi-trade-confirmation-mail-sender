"""
Service for resolving/creating the report output directory.

``set_report_output_dir`` is called once per report run (from the reports
endpoint) with the trading date. It creates the date-specific output folder
and caches it so downstream services (e.g. :mod:`app.services.pdf_service`)
can reuse it without re-deriving the path on every call.
"""
import os

from app.core.config import get_settings

# Module-level cache of the report output directory for the current run.
_dir_path: str | None = None


def set_report_output_dir(trading_date: str) -> str:
    """
    Create (or reuse) and cache the date-specific report output folder.

    Returns the absolute path to the folder, e.g.
    ``<REPORT_OUTPUT_DIR>/2026-08-31``.
    """
    global _dir_path
    output_dir = get_settings().report_output_dir
    dir_path = os.path.join(str(output_dir), trading_date)
    os.makedirs(dir_path, exist_ok=True)
    _dir_path = dir_path
    return dir_path


def get_report_output_dir() -> str | None:
    """Return the cached report output directory, or ``None`` if not set."""
    return _dir_path


def report_dir_for_date(trading_date: str) -> str:
    """
    Return the absolute output folder for ``trading_date`` WITHOUT mutating
    the cache or creating the directory. Useful for read-only lookups such as
    listing/downloading already-generated reports.
    """
    output_dir = get_settings().report_output_dir
    return os.path.join(str(output_dir), trading_date)