"""
Report generation endpoints.

- ``POST`` endpoints generate report(s) and write PDFs to disk (side effects).
- ``GET`` endpoints only list / download already-generated reports (pure reads).

Generation uses POST because it performs side effects (writes files), can be
slow when generating reports for many clients, and is intended to be triggered
explicitly rather than via GET-safe operations like browser navigation or link
previews.
"""
import os

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import FileResponse
from duckdb import DuckDBPyConnection

from app.api.deps import get_db
from app.schemas.trade import (
    SingleClientTradeConfirmationRequest,
    TradeConfirmationRequest,
)
from app.services.trade_summary_service import generate_client_trade_summary_json
from app.services.pdf_service import generate_trade_confirmation
from app.services.dir_service import set_report_output_dir, report_dir_for_date
from app.services.logger_service import setup_logger
import time


logger = setup_logger('reports_logger', 'reports.log')
mail_logger = setup_logger('mail_logger', 'mail.log')


router = APIRouter(tags=["reports"])


def _send_mail_with_report_attachment(file_path: str, recipient_email: str = 'test@example.com') -> None:
    # Placeholder for future implementation of email sending functionality
    time.sleep(3)
    mail_logger.info(f"Simulated sending email with attachment '{file_path}' to '{recipient_email}'")


def _generate_client_trade_confirmation(
    client_code: str,
    trading_date: str,
    background_tasks: BackgroundTasks,
    conn: DuckDBPyConnection,
) -> None:
    """Shared logic: build summary JSON and write the PDF. Raises on failure."""
    try:
        trade_summary = generate_client_trade_summary_json(client_code, trading_date, conn)
        attachment_path = generate_trade_confirmation(
            trade_summary,
            output_file=f"Trade_Confirmation_{client_code}.pdf",
        )
        logger.info(f"Generated report for client '{client_code}' on {trading_date}")
        background_tasks.add_task(_send_mail_with_report_attachment, attachment_path, f"{client_code}@example.com")
    except Exception as e:  # noqa: BLE001
        logger.error(f"Failed to generate report for client '{client_code}' on {trading_date}: {e}")
        raise HTTPException(
            status_code=500,
            detail={"msg": "report generation failed", "error": str(e)},
        )


def _generate_client_trade_confirmation_to_all(
    client_codes: list[str],
    trading_date: str,
    background_tasks: BackgroundTasks,
    conn: DuckDBPyConnection,
) -> None:
    for client_code in client_codes:
        try:
            _generate_client_trade_confirmation(client_code, trading_date, background_tasks, conn)
        except HTTPException as e:
            # Don't let one client's failure stop the rest of the batch.
            logger.error(f"Skipping client '{client_code}' on {trading_date}: {e.detail}")


@router.post("/trade-confirmation-report/single", status_code=201)
async def generate_single_client_report(
    payload: SingleClientTradeConfirmationRequest,
    background_tasks: BackgroundTasks,
    conn: DuckDBPyConnection = Depends(get_db),
):
    """
    Generate a trade confirmation PDF for a single client on a trading date.

    Body: ``{"trading_date": "2026-08-31", "client_code": "F0001"}``

    The PDF is written under ``<REPORT_OUTPUT_DIR>/<trading_date>/``.
    """

    set_report_output_dir(payload.trading_date)

    background_tasks.add_task(
        _generate_client_trade_confirmation,
        payload.client_code,
        payload.trading_date,
        background_tasks,
        conn,
    )

    return {
        "msg": "report generation started",
    }


@router.post("/trade-confirmation-report/all", status_code=201)
async def generate_all_clients_report(
    payload: TradeConfirmationRequest,
    background_tasks: BackgroundTasks,
    conn: DuckDBPyConnection = Depends(get_db),
):
    """
    Generate trade confirmation PDFs for every client that traded on the date.

    Body: ``{"trading_date": "2026-08-31"}``

    PDFs are written under ``<REPORT_OUTPUT_DIR>/<trading_date>/``.
    """
    client_codes_df = conn.execute(
        """
        SELECT DISTINCT client_code
        FROM tbl_trade_info
        WHERE trading_date = ?
        ORDER BY client_code
        """,
        [payload.trading_date],
    ).df()

    if client_codes_df.empty:
        return {
            "msg": "no trades found for the requested date",
            "total": 0,
            "success": 0,
            "failed": 0,
        }

    set_report_output_dir(payload.trading_date)

    background_tasks.add_task(
        _generate_client_trade_confirmation_to_all,
        client_codes_df["client_code"].tolist(),
        payload.trading_date,
        background_tasks,
        conn,
    )

    return {
        "msg": f"report generation started for {len(client_codes_df)} clients",
    }