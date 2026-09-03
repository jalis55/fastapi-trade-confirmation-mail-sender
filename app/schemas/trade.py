"""Request/response schemas for the trade confirmation API."""
from pydantic import BaseModel


class OpeningBalanceResponse(BaseModel):
    """Response body for GET /api/v1/account/opening-balance."""

    client_code: str
    opening_balance: float
    trading_date: str


class TradeConfirmationRequest(BaseModel):
    """
    Request body for generating trade confirmation reports for ALL clients
    that traded on ``trading_date``.
    """

    trading_date: str


class SingleClientTradeConfirmationRequest(TradeConfirmationRequest):
    """
    Request body for generating a trade confirmation report for a single client
    on a specific trading date.
    """

    client_code: str