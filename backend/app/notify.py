"""Delivers fraud events to the n8n workflow (backend/n8n/The-Safest-Bank.json).

ESCROW_HELD events carry the OTP; n8n emails it to the account holder.
AUTO_ABORT events alert the SOC channel and carry no OTP.
"""

import logging

import httpx

from app.config import settings

log = logging.getLogger("uvicorn.error")
_transport = None  # tests swap in httpx.MockTransport


async def send(payload: dict) -> None:
    if not settings.n8n_webhook_url:
        if settings.demo_mode and payload.get("otp_code"):
            log.warning("[DEMO] N8N_WEBHOOK_URL not set. OTP for %s: %s", payload["transaction_id"], payload["otp_code"])
        return
    headers = {"X-Webhook-Secret": settings.n8n_webhook_secret} if settings.n8n_webhook_secret else {}
    try:
        async with httpx.AsyncClient(timeout=5.0, transport=_transport) as client:
            (await client.post(settings.n8n_webhook_url, json=payload, headers=headers)).raise_for_status()
    except httpx.HTTPError as exc:
        # Delivery failure must never break the ledger; the transfer stays held for the SOC.
        log.warning("n8n delivery failed for %s: %s", payload.get("transaction_id"), exc)
