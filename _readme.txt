# Trade Confirmation API

A FastAPI service that generates **Trade Confirmation Note (Summary) PDFs** from
trade data stored in a DuckDB database, using ReportLab for PDF rendering.

## Features

- `GET /api/v1/account/opening-balance` â€” opening balance for a client on a trading date
- `POST /trade-confirmation-report` â€” generate trade confirmation PDF(s) for a trading date
  - body `{"trading_date": "2026-08-31"}` â†’ all clients that traded that day
  - body `{"trading_date": "2026-08-31", "client_code": "F0001"}` â†’ just one client
- `GET /reports?trading_date=...` â€” list already-generated PDFs (read-only)
- `GET /reports/download?trading_date=...&client_code=...` â€” download an existing PDF
- `GET /test-db` â€” list the tables present in the configured database

## Project structure

```
terade_conf/
â”œâ”€â”€ app/                          # application package
â”‚   â”œâ”€â”€ main.py                   # FastAPI app + router registration
â”‚   â”œâ”€â”€ api/                      # presentation layer
â”‚   â”‚   â”œâ”€â”€ deps.py               # shared dependencies (request-scoped DB connection)
â”‚   â”‚   â””â”€â”€ v1/endpoints/         # versioned HTTP routers
â”‚   â”‚       â”œâ”€â”€ health.py         # GET /test-db
â”‚   â”‚       â”œâ”€â”€ account.py        # opening-balance
â”‚   â”‚       â””â”€â”€ reports.py        # trade-confirmation-report
â”‚   â”œâ”€â”€ core/
â”‚   â”‚   â””â”€â”€ config.py             # environment-driven settings
â”‚   â”œâ”€â”€ db/
â”‚   â”‚   â””â”€â”€ connection.py         # DuckDB connection management
â”‚   â”œâ”€â”€ schemas/
â”‚   â”‚   â””â”€â”€ trade.py              # Pydantic response models
â”‚   â””â”€â”€ services/
â”‚       â”œâ”€â”€ trade_summary_service.py  # builds the per-client trade summary
â”‚       â””â”€â”€ pdf_service.py            # renders the PDF report
â”œâ”€â”€ data/                         # DuckDB database (gitignored)
â”‚   â””â”€â”€ trades_db.duckdb
â”œâ”€â”€ output/                       # generated PDFs (gitignored)
â”‚   â””â”€â”€ trade_confirmations/<trading_date>/
â””â”€â”€ ...config files
```

## Setup

Requires Python 3.14 (managed with [uv](https://docs.astral.sh/uv/)).

```bash
uv sync
uv run uvicorn app.main:app --reload
```

Or using the existing virtual environment:

```bash
.\.venv\Scripts\activate
uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000/docs> for the interactive API documentation.

## Configuration

Runtime settings are read from environment variables (see `.env.example`):

| Variable            | Default                                   | Description                        |
|---------------------|-------------------------------------------|------------------------------------|
| `TRADE_DB_PATH`     | `<root>/data/trades_db.duckdb`            | DuckDB database file               |
| `REPORT_OUTPUT_DIR` | `<root>/output/trade_confirmations`       | Base folder for generated PDFs     |
| `APP_NAME`          | `Trade Confirmation API`                  | App title (shown in /docs)         |
| `APP_VERSION`       | `1.0.0`                                   | App version                        |

## Example

```bash
# Generate reports for all clients that traded on 2026-08-31
curl "http://127.0.0.1:8000/trade-confirmation-report?trading_date=2026-08-31"
```

PDFs are written to `output/trade_confirmations/2026-08-31/`.

