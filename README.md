# Trade Confirmation API

A FastAPI service that generates **Trade Confirmation Note (Summary) PDFs** from
trade data stored in a DuckDB database, using ReportLab for PDF rendering.

## Features

- `GET /api/v1/account/opening-balance` — opening balance for a client on a trading date
- `POST /trade-confirmation-report/single` — generate a trade confirmation PDF for **one** client
  - body `{"trading_date": "2026-08-31", "client_code": "F0001"}`
- `POST /trade-confirmation-report/all` — generate trade confirmation PDFs for **all** clients that traded on the date
  - body `{"trading_date": "2026-08-31"}`
- `GET /reports?trading_date=...` — list already-generated PDFs (read-only)
- `GET /reports/download?trading_date=...&client_code=...` — download an existing PDF
- `GET /test-db` — list the tables present in the configured database

## Project structure

```
terade_conf/
├── app/                          # application package
│   ├── main.py                   # FastAPI app + router registration
│   ├── api/                      # presentation layer
│   │   ├── deps.py               # shared dependencies (request-scoped DB connection)
│   │   └── v1/endpoints/         # versioned HTTP routers
│   │       ├── health.py         # GET /test-db
│   │       ├── account.py        # opening-balance
│   │       └── reports.py        # trade-confirmation-report
│   ├── core/
│   │   └── config.py             # environment-driven settings
│   ├── db/
│   │   └── connection.py         # DuckDB connection management
│   ├── schemas/
│   │   └── trade.py              # Pydantic response models
│   └── services/
│       ├── trade_summary_service.py  # builds the per-client trade summary
│       └── pdf_service.py            # renders the PDF report
├── data/                         # DuckDB database (gitignored)
│   └── trades_db.duckdb
├── output/                       # generated PDFs (gitignored)
│   └── trade_confirmations/<trading_date>/
└── ...config files
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
# Generate a report for just one client
curl -X POST "http://127.0.0.1:8000/trade-confirmation-report/single" \
  -H "Content-Type: application/json" \
  -d '{"trading_date": "2026-08-31", "client_code": "F0001"}'

# Generate reports for all clients that traded on 2026-08-31
curl -X POST "http://127.0.0.1:8000/trade-confirmation-report/all" \
  -H "Content-Type: application/json" \
  -d '{"trading_date": "2026-08-31"}'
```

PDFs are written to `output/trade_confirmations/2026-08-31/`. To list or download
existing reports:

```bash
# List already-generated reports
curl "http://127.0.0.1:8000/reports?trading_date=2026-08-31"

# Download one
curl -O "http://127.0.0.1:8000/reports/download?trading_date=2026-08-31&client_code=F0001"
```
