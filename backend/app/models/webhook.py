"""
Webhook models for TradingView x Dhan Trading System
Phase 2: Webhook ingestion + idempotency
"""

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class TradingViewWebhook(BaseModel):
    """TradingView webhook payload schema"""
    id: str = Field(..., description="Unique identifier for the alert")
    symbol: Literal["NIFTY", "BANKNIFTY"] = Field(..., description="Index symbol")
    signal: Literal["BUY CE", "SELL CE", "BUY PE", "SELL PE"] = Field(..., description="Trading signal")
    ts: datetime = Field(..., description="ISO timestamp")


class WebhookResponse(BaseModel):
    """Webhook response schema"""
    status: str = Field(..., description="Response status")
    message: str = Field(..., description="Response message")
