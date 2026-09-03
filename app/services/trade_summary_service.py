"""
Service that builds the trade summary (JSON-ready dict) for a client on a date.
"""
import pandas as pd


def generate_client_trade_summary_json(client_code_to_fetch, trading_date_to_fetch, conn):
    """
    Generates a detailed trade summary dictionary for a given client and trading date.

    Args:
        client_code_to_fetch (str): The client code to filter by.
        trading_date_to_fetch (str): The trading date (YYYY-MM-DD) to filter by.
        conn (duckdb.DuckDBPyConnection): The DuckDB connection object.

    Returns:
        dict: A dictionary containing the client's trade summary for the specified date.
    """
    # 1. Fetch client's opening balance from tbl_account
    opening_balance_query = conn.execute(
        "SELECT opening_balance FROM tbl_account WHERE client_code = ?",
        [client_code_to_fetch]
    ).df()
    client_opening_balance = opening_balance_query['opening_balance'].iloc[0] if not opening_balance_query.empty else 0.0

    # 2. Fetch all trade info for the given client and trading date
    trades_df = conn.execute(
        """
        SELECT
            client_code,
            name AS client_name,
            boid AS bo_id,
            market,
            trans_type,
            exchange,
            instrument_name AS instrument,
            total_qty AS qty,
            avg_rate,
            amount,
            commission,
            balance,
            trading_date
        FROM tbl_trade_info
        WHERE client_code = ? AND trading_date = ?
        """,
        [client_code_to_fetch, trading_date_to_fetch]
    ).df()

    # Initialize the dictionary structure
    generated_data = {
        "client_code": client_code_to_fetch,
        "client_name": "",
        "bo_id": "",
        "trading_date": trading_date_to_fetch,
        "buy_transactions": [],
        "sell_transactions": [],
        "opening_balance": client_opening_balance,
        "closing_balance": client_opening_balance,  # Will be updated
    }

    if not trades_df.empty:
        # Populate client_name and bo_id from the first row of transactions
        # Ensure bo_id is treated as a string to avoid potential issues with large integers
        generated_data["client_name"] = trades_df['client_name'].iloc[0]
        generated_data["bo_id"] = str(trades_df['bo_id'].iloc[0])

        total_daily_balance_change = 0.0

        # Iterate through transactions to populate buy_transactions and sell_transactions
        for _, row in trades_df.iterrows():
            transaction_details = {
                "market": row['market'],
                "trans_type": row['trans_type'],
                "exchange": row['exchange'],
                "instrument": row['instrument'],
                "qty": int(row['qty']),  # Ensure qty is integer
                "avg_rate": float(row['avg_rate']),
                "amount": float(row['amount']),
                "commission": float(row['commission']),
                "balance": float(row['balance']),
            }

            if row['trans_type'] == 'BUY':
                generated_data["buy_transactions"].append(transaction_details)
                # Cash decreases on buy (assuming balance here is total cost including commission)
                total_daily_balance_change -= float(row['balance'])
            elif row['trans_type'] == 'SELL':
                generated_data["sell_transactions"].append(transaction_details)
                # Cash increases on sell (assuming balance here is total proceeds including commission)
                total_daily_balance_change += float(row['balance'])

        # Calculate closing balance for the day
        generated_data["closing_balance"] = client_opening_balance + total_daily_balance_change

    return generated_data