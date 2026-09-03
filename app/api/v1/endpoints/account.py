"""
Account endpoints.
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from duckdb import DuckDBPyConnection

from app.api.deps import get_db
from app.schemas.trade import OpeningBalanceResponse
from app.services.logger_service import setup_logger


logger = setup_logger("account_logger", "account.log")

router = APIRouter(prefix="/api/v1/account", tags=["account"])


@router.get("/opening-balance", response_model=OpeningBalanceResponse)
def get_opening_balance(
    client_code: str = Query(..., description="Client code (e.g., F0001)"),
    trading_date: str = Query(..., description="Date in YYYY-MM-DD format"),
    conn: DuckDBPyConnection = Depends(get_db),
):
    """
    Get the opening balance for a specific client on a specific trading date.

    The opening balance is the client's opening balance from ``tbl_account``
    adjusted by the net of the day's SELL/BUY transactions.
    """
    # Validate date format
    try:
        date.fromisoformat(trading_date)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format. Use YYYY-MM-DD",
        )

    # Check if client exists
    client = conn.execute(
        "SELECT opening_balance FROM tbl_account WHERE client_code = ?",
        [client_code],
    ).fetchone()

    if not client:
        raise HTTPException(
            status_code=404,
            detail=f"Client '{client_code}' not found",
        )

    # Get opening balance for the specific date
    result = conn.execute(
        """
        WITH trade_balance AS (
            SELECT
                SUM(CASE
                    WHEN trans_type = 'BUY' THEN -amount
                    WHEN trans_type = 'SELL' THEN amount
                    ELSE 0
                END) as net_change
            FROM tbl_trade_info
            WHERE client_code = ? AND trading_date = ?
        )
        SELECT
            a.opening_balance + COALESCE(t.net_change, 0) as balance
        FROM tbl_account a
        CROSS JOIN trade_balance t
        WHERE a.client_code = ?
        """,
        [client_code, trading_date, client_code],
    ).fetchone()

    if not result or result[0] is None:
        # If no trades on this date, return the opening balance
        logger.warning(f"No trades found for client {client_code} on {trading_date}. Returning opening balance.")
        return OpeningBalanceResponse(
            client_code=client_code,
            opening_balance=float(client[0]),
            trading_date=trading_date,
        )
    logger.info(f"Checking opening balance for client {client_code} on {trading_date}")
    return OpeningBalanceResponse(
        client_code=client_code,
        opening_balance=float(result[0]),
        trading_date=trading_date,
    )