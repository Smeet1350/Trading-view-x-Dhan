"""
Webhook API router for TradingView x Dhan Trading System
Phase 2: Webhook ingestion + idempotency
"""

import os
from fastapi import APIRouter, HTTPException, Header, Depends
from fastapi.responses import JSONResponse

from ..models.webhook import TradingViewWebhook, WebhookResponse
from ..services.alert_service import get_alert_service

router = APIRouter(prefix="/webhook", tags=["webhook"])


async def verify_webhook_token(x_webhook_token: str = Header(None)) -> str:
    """Verify webhook authentication token"""
    if not x_webhook_token:
        raise HTTPException(status_code=401, detail="Missing X-WEBHOOK-TOKEN header")
    
    expected_token = os.getenv("WEBHOOK_TOKEN", "test_webhook_token")
    if x_webhook_token != expected_token:
        raise HTTPException(status_code=401, detail="Invalid webhook token")
    
    return x_webhook_token


@router.post("/", response_model=WebhookResponse)
async def tradingview_webhook(
    alert: TradingViewWebhook,
    token: str = Depends(verify_webhook_token)
) -> WebhookResponse:
    """
    POST /webhook endpoint for TradingView alerts
    
    Expects JSON payload with:
    - id: unique identifier
    - symbol: NIFTY or BANKNIFTY
    - signal: BUY CE, SELL CE, BUY PE, or SELL PE
    - ts: ISO timestamp
    
    Returns:
    - {"status": "duplicate"} if alert already processed
    - {"status": "accepted"} if new alert stored
    """
    
    # Get alert service
    alert_service = get_alert_service()
    
    # Check for duplicates using SHA256 hash
    if alert_service.is_duplicate(alert):
        return WebhookResponse(
            status="duplicate",
            message="Alert already processed"
        )
    
    # Store the new alert
    if alert_service.store_alert(alert):
        return WebhookResponse(
            status="accepted",
            message="Alert stored successfully"
        )
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to store alert"
        )


@router.get("/status")
async def webhook_status():
    """Get webhook endpoint status and alert count"""
    alert_service = get_alert_service()
    return {
        "status": "active",
        "phase": "2",
        "alert_count": alert_service.get_alert_count(),
        "message": "Webhook endpoint is active"
    }
