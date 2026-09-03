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

from fastapi import APIRouter, Depends, HTTPException, Query
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

router = APIRouter(tags=["reports"])


def _generate_client_trade_confirmation(
    client_code: str,
    trading_date: str,
    conn: DuckDBPyConnection,
) -> None:
    """Shared logic: build summary JSON and write the PDF. Raises on failure."""
    trade_summary = generate_client_trade_summary_json(client_code, trading_date, conn)
    generate_trade_confirmation(
        trade_summary,
        output_file=f"Trade_Confirmation_{client_code}.pdf",
    )


@router.post("/trade-confirmation-report/single", status_code=201)
def generate_single_client_report(
    payload: SingleClientTradeConfirmationRequest,
    conn: DuckDBPyConnection = Depends(get_db),
):
    """
    Generate a trade confirmation PDF for a single client on a trading date.

    Body: ``{"trading_date": "2026-08-31", "client_code": "F0001"}``

    The PDF is written under ``<REPORT_OUTPUT_DIR>/<trading_date>/``.
    """
    set_report_output_dir(payload.trading_date)
    try:
        _generate_client_trade_confirmation(payload.client_code, payload.trading_date, conn)
        return {
            "msg": "report generated",
            "status": "success",
            "client_code": payload.client_code,
        }
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail={"msg": "report generation failed", "error": str(e)},
        )


@router.post("/trade-confirmation-report/all", status_code=201)
def generate_all_clients_report(
    payload: TradeConfirmationRequest,
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

    success_count = 0
    failed_count = 0
    errors = []

    for _, row in client_codes_df.iterrows():
        client_code = row["client_code"]
        try:
            _generate_client_trade_confirmation(client_code, payload.trading_date, conn)
            success_count += 1
        except Exception as e:  # noqa: BLE001
            failed_count += 1
            errors.append({"client_code": client_code, "error": str(e)})

    return {
        "msg": "report generation completed",
        "total": success_count + failed_count,
        "success": success_count,
        "failed": failed_count,
        "errors": errors,  # empty list if all succeeded
    }


@router.get("/reports")
def list_generated_reports(
    trading_date: str = Query(..., description="Date in YYYY-MM-DD format"),
):
    """
    List the PDF reports already generated for ``trading_date``.

    Read-only: does not generate any reports or create any folders.
    """
    report_dir = report_dir_for_date(trading_date)

    if not os.path.isdir(report_dir):
        return {"trading_date": trading_date, "reports": []}

    reports = [
        name
        for name in sorted(os.listdir(report_dir))
        if name.lower().endswith(".pdf")
    ]
    return {"trading_date": trading_date, "reports": reports}


@router.get("/reports/download")
def download_generated_report(
    trading_date: str = Query(..., description="Date in YYYY-MM-DD format"),
    client_code: str = Query(..., description="Client code (e.g., F0001)"),
):
    """
    Download an already-generated report for a client on a trading date.

    Read-only: returns the existing PDF file if present.
    """
    report_dir = report_dir_for_date(trading_date)
    report_path = os.path.join(report_dir, f"Trade_Confirmation_{client_code}.pdf")

    if not os.path.isfile(report_path):
        raise HTTPException(
            status_code=404,
            detail=f"No report found for client '{client_code}' on {trading_date}",
        )

    return FileResponse(
        report_path,
        media_type="application/pdf",
        filename=f"Trade_Confirmation_{client_code}.pdf",
    )