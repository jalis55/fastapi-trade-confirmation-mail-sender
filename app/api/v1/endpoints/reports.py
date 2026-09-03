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
from app.services.celery_service import celery_app
import time


logger = setup_logger('reports_logger', 'reports.log')
mail_logger = setup_logger('mail_logger', 'mail.log')


router = APIRouter(tags=["reports"])


def _send_mail_with_report_attachment(file_path: str, recipient_email: str = 'test@example.com') -> None:
    # Placeholder for future implementation of email sending functionality
    time.sleep(3)
    mail_logger.info(f"Simulated sending email with attachment '{file_path}' to '{recipient_email}'")


@celery_app.task(name="generate_client_trade_confirmation_task", bind=True)
def generate_client_trade_confirmation_task(self, client_code: str, trading_date: str):
    """Celery task that runs asynchronously in separate worker"""
    try:
        # Open a fresh DB connection inside the task (closed in finally below)
        from app.db.connection import get_db_connection
        conn = get_db_connection()
        try:
            trade_summary = generate_client_trade_summary_json(client_code, trading_date, conn)
            attachment_path = generate_trade_confirmation(
                trade_summary,
                output_file=f"Trade_Confirmation_{client_code}.pdf",
            )
        finally:
            conn.close()

        logger.info(f"Generated report for client '{client_code}' on {trading_date}")

        # Send email asynchronously within the task
        _send_mail_with_report_attachment(attachment_path, f"{client_code}@example.com")

        return {"status": "success", "client_code": client_code}
    except Exception as e:
        logger.error(f"Failed for client '{client_code}': {e}")
        raise

@router.post("/trade-confirmation-report/single", status_code=202)
async def generate_single_client_report(
    payload: SingleClientTradeConfirmationRequest,
    conn: DuckDBPyConnection = Depends(get_db),
):
    """Submit a single report generation task to Celery"""
    set_report_output_dir(payload.trading_date)
    
    # Submit to Celery - returns immediately
    task = generate_client_trade_confirmation_task.delay(
        payload.client_code,
        payload.trading_date
    )
    
    return {
        "msg": "report generation started",
        "task_id": task.id,
        "status_url": f"/tasks/{task.id}"
    }

@router.post("/trade-confirmation-report/all", status_code=202)
async def generate_all_clients_report(
    payload: TradeConfirmationRequest,
    conn: DuckDBPyConnection = Depends(get_db),
):
    """Submit batch of report generation tasks to Celery"""
    client_codes_df = conn.execute(
        f"""
        SELECT DISTINCT client_code
        FROM tbl_trade_info
        WHERE trading_date = '{payload.trading_date}'
        ORDER BY client_code
        LIMIT 1000
        """
    ).df()
    
    if client_codes_df.empty:
        return {"msg": "no trades found", "total": 0}
    
    set_report_output_dir(payload.trading_date)
    
    # Submit ALL tasks in parallel (Celery handles concurrency)
    tasks = []
    for client_code in client_codes_df["client_code"].tolist():
        task = generate_client_trade_confirmation_task.delay(
            client_code,
            payload.trading_date
        )
        tasks.append({"client_code": client_code, "task_id": task.id})
    
    return {
        "msg": f"submitted {len(tasks)} report generation tasks",
        "total": len(tasks),
        "tasks": tasks
    }