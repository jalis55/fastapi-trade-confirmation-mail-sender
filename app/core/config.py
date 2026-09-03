"""
Application settings.

Values are read from environment variables (with sane defaults) so the
application can be configured without code changes. Paths are resolved
relative to the project root (the parent of the ``app`` package).
"""
import os
from functools import lru_cache
from pathlib import Path

# Root of the project = parent of the directory that contains this file:
#   <root>/app/core/config.py  ->  <root>
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings:
    """Runtime configuration for the API."""

    def __init__(self) -> None:
        self.app_name: str = os.getenv("APP_NAME", "Trade Confirmation API")
        self.app_version: str = os.getenv("APP_VERSION", "1.0.0")
        self.app_description: str = os.getenv(
            "APP_DESCRIPTION",
            "Generates trade confirmation reports from DuckDB trade data.",
        )

        # Path to the DuckDB database file containing tbl_account / tbl_trade_info
        self.db_path: Path = Path(
            os.getenv("TRADE_DB_PATH", str(PROJECT_ROOT / "data" / "trades_db.duckdb"))
        )

        # Base directory where generated PDF reports are written. Each report is
        # saved under <REPORT_OUTPUT_DIR>/<trading_date>/Trade_Confirmation_<client_code>.pdf
        self.report_output_dir: Path = Path(
            os.getenv(
                "REPORT_OUTPUT_DIR",
                str(PROJECT_ROOT / "trade_confirmations"),
            )
        )


@lru_cache
def get_settings() -> Settings:
    """
    Return a cached ``Settings`` instance.

    Cached so every module shares the same configuration for the process.
    """
    return Settings()