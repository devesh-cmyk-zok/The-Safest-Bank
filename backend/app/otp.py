"""Step-up OTPs for held transfers. Stored as an HMAC on the transaction row, never in clear."""

import hashlib
import hmac
import secrets
from datetime import timedelta, timezone

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.config import settings
from database.models import Transaction, utcnow

TTL = timedelta(minutes=5)
MAX_ATTEMPTS = 5


def _digest(tx_id: str, code: str) -> str:
    return hmac.new(settings.service_api_key.encode(), f"{tx_id}:{code}".encode(), hashlib.sha256).hexdigest()


def issue(tx: Transaction) -> str:
    """Set a fresh code on the transaction (caller commits) and return it for delivery."""
    code = f"{secrets.randbelow(1_000_000):06d}"
    tx.otp_hash = _digest(tx.id, code)
    tx.otp_expires_at = utcnow() + TTL
    tx.otp_attempts = 0
    return code


def check(db: Session, tx: Transaction, code: str) -> str:
    """Returns "ok", "invalid", "expired" or "locked". Commits the attempt count."""
    if tx.otp_hash is None:
        return "locked"
    expires = tx.otp_expires_at
    if expires.tzinfo is None:  # SQLite hands back naive UTC
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < utcnow():
        return "expired"
    # Atomic increment: concurrent guesses can't slip past the limit.
    counted = db.execute(
        update(Transaction)
        .where(Transaction.id == tx.id, Transaction.otp_attempts < MAX_ATTEMPTS)
        .values(otp_attempts=Transaction.otp_attempts + 1)
    ).rowcount
    db.commit()
    if not counted:
        return "locked"
    if hmac.compare_digest(tx.otp_hash, _digest(tx.id, (code or "").strip())):
        return "ok"
    db.refresh(tx)
    return "locked" if tx.otp_attempts >= MAX_ATTEMPTS else "invalid"
