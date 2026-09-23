"""
FILE: app/webhook.py
PURPOSE:
    Asynchronous incident dispatcher.
    Sends quarantined transaction telemetry to downstream automation
    endpoints (e.g., n8n, SOC agents) without blocking the primary ledger thread.
"""

import httpx
import logging
from typing import Dict, Any

logger = logging.getLogger("uvicorn.error")

# Configure target webhook URL (e.g., Juhili's n8n webhook or a webhook.site test URL)
# Can be overridden via environment variables
DEFAULT_WEBHOOK_URL = "https://webhook.site/228c29c7-68f0-4d9c-a762-9649e1d647db"

async def dispatch_quarantine_event(
    transaction_id: str,
    user_id: str,
    recipient_id: str,
    amount: float,
    risk_score: float,
    xai_breakdown: Dict[str, Any],
    webhook_url: str = DEFAULT_WEBHOOK_URL
):
    payload = {
        "event": "ESCROW_QUARANTINE_TRIGGERED",
        "transaction_id": transaction_id,
        "user_id": user_id,
        "recipient_id": recipient_id,
        "amount": amount,
        "risk_score": risk_score,
        "xai_breakdown": xai_breakdown
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(webhook_url, json=payload)
            logger.info(f"Dispatched escrow event for {transaction_id}. Status: {response.status_code}")
    except Exception as exc:
        # Non-blocking: failure to notify external systems must not crash the banking ledger
        logger.warning(f"Failed to dispatch escrow webhook for {transaction_id}: {str(exc)}")