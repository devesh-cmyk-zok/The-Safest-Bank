"""Turns a transfer request into the six fraud signals the engine scores.

Everything except typing cadence (browser) and distance (demo simulation only; there is
no GeoIP lookup) is computed from the bank's own records, never taken from the client.
"""

import math
import statistics
from dataclasses import asdict, dataclass
from datetime import timedelta
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database.models import KnownDevice, Transaction, TxStatus, utcnow

FEATURES = ["amount_ratio", "velocity_1h", "new_payee", "new_device", "cadence", "distance"]
BASELINE_FLOOR_PAISE = 100_000  # ₹1,000: new accounts aren't flagged for every ordinary payment


@dataclass
class Signals:
    amount_ratio: float  # amount / sender's median recent payment
    velocity_1h: int  # sender's transfers in the last hour
    new_payee: bool  # never paid this recipient successfully before
    new_device: bool  # device not registered to this account
    cadence_ms: Optional[float]  # median keystroke interval on the form; None = not measured
    distance_km: float  # distance from usual location (simulated only)

    def as_dict(self) -> dict:
        return asdict(self)


def gather(db: Session, user_id: str, recipient_id: str, amount_paise: int,
           device_id: str, cadence_ms: Optional[float], distance_km: float) -> Signals:
    recent = db.scalars(
        select(Transaction.amount_paise)
        .where(Transaction.user_id == user_id, Transaction.status == TxStatus.SETTLED)
        .order_by(Transaction.created_at.desc())
        .limit(20)
    ).all()
    baseline = max(statistics.median(recent) if recent else 0, BASELINE_FLOOR_PAISE)

    velocity = db.scalar(
        select(func.count()).select_from(Transaction)
        .where(Transaction.user_id == user_id, Transaction.created_at >= utcnow() - timedelta(hours=1))
    )
    paid_before = db.scalar(
        select(func.count()).select_from(Transaction)
        .where(Transaction.user_id == user_id, Transaction.recipient_id == recipient_id,
               Transaction.status == TxStatus.SETTLED)
    )
    devices = set(db.scalars(select(KnownDevice.device_id).where(KnownDevice.user_id == user_id)))

    return Signals(
        amount_ratio=round(amount_paise / baseline, 3),
        velocity_1h=int(velocity or 0),
        new_payee=not paid_before,
        # Trust on first use: an account with no registered device adopts the first one.
        new_device=bool(devices) and device_id not in devices,
        cadence_ms=cadence_ms,
        distance_km=float(distance_km or 0.0),
    )


def cadence_risk(ms: Optional[float]) -> float:
    if ms is None:
        return 0.3  # unknown: mild, pasting or picking from a list is normal
    if ms < 40:
        return 1.0  # faster than human typing: scripted input
    if ms < 70:
        return 0.6
    if ms <= 600:
        return 0.0  # normal human rhythm
    if ms <= 1500:
        return 0.2
    return 0.5  # very slow, hesitant entry: typical of a victim being coached on the phone


def _log_scale(value: float, lo: float, hi: float) -> float:
    if value <= lo:
        return 0.0
    return min(1.0, math.log(value / lo) / math.log(hi / lo))


def risks(s: Signals) -> dict:
    """Map raw signals to per-signal risks in [0, 1]. Same code for training and serving."""
    return {
        "amount_ratio": _log_scale(s.amount_ratio, 1.0, 20.0),  # 20x usual = max
        "velocity_1h": min(s.velocity_1h / 5.0, 1.0),
        "new_payee": 1.0 if s.new_payee else 0.0,
        "new_device": 1.0 if s.new_device else 0.0,
        "cadence": cadence_risk(s.cadence_ms),
        "distance": _log_scale(s.distance_km, 50.0, 2000.0),
    }
