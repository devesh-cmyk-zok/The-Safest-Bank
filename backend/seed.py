"""Create demo customers, 30 days of ordinary history, and a few live fraud scenarios.

    python backend/seed.py           # seed an empty database
    python backend/seed.py --reset   # drop everything and reseed (destroys data!)

Scenario transfers go through the real API route, so the SOC sees exactly what the
pipeline decides. n8n delivery is switched off while seeding.
"""

import os
import random
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi.testclient import TestClient  # noqa: E402

from app import ledger, main  # noqa: E402
from app.config import settings  # noqa: E402
from database.connection import Base, SessionLocal, engine  # noqa: E402
from database.models import KnownDevice, Transaction, TxStatus, User, utcnow  # noqa: E402

# id, name, handle, opening balance (₹), regular payees
CUSTOMERS = [
    ("usr_1001", "Aarav Sharma", "aarav", 1_50_000, ["usr_1002", "usr_1003"]),
    ("usr_1002", "Priya Patel", "priya", 1_20_000, ["usr_1001", "usr_1004"]),
    ("usr_1003", "Rohan Mehta", "rohan", 90_000, ["usr_1001", "usr_1005"]),
    ("usr_1004", "Ananya Iyer", "ananya", 2_00_000, ["usr_1002", "usr_1003"]),
    ("usr_1005", "Vikram Singh", "vikram", 75_000, ["usr_1003", "usr_1004"]),
    ("usr_9999", "QuickCash Services", "quickcash", 0, []),  # mule account fraudsters pay into
]
# The logins you demo with start with no registered device, so the first browser you use
# is trusted on first use. Everyone else "owns" a phone that the scripted scenarios use.
DEMO_LOGINS = {"usr_1001", "usr_1002"}


def _email(handle: str) -> str:
    inbox = os.getenv("DEMO_OTP_EMAIL", "").strip()
    if inbox and "@" in inbox:
        local, domain = inbox.split("@", 1)
        return f"{local}+{handle}@{domain}"
    return f"{handle}@example.com"


def seed_history(db) -> int:
    rng = random.Random(42)
    now = utcnow()
    for uid, name, handle, balance, _ in CUSTOMERS:
        db.add(User(id=uid, full_name=name, email=_email(handle), balance_paise=balance * 100))
        if uid not in DEMO_LOGINS and uid != "usr_9999":
            db.add(KnownDevice(user_id=uid, device_id=f"seed-{handle}-phone"))
    db.flush()

    n = 0
    for uid, _, handle, _, payees in CUSTOMERS:
        if not payees:
            continue
        for i in range(rng.randint(12, 18)):
            paise = rng.choice([500, 800, 1200, 1500, 2000, 2500, 3000, 4500]) * 100
            ledger.open_transfer(db, Transaction(
                id=f"tx_seed_{handle}_{i:02d}", user_id=uid, recipient_id=rng.choice(payees),
                amount_paise=paise, status=TxStatus.SETTLED, risk_score=round(rng.uniform(0.01, 0.12), 4),
                assessment={"reasons": [], "soc_report": {"severity": "LOW"}},
                device_id=f"seed-{handle}-phone",
                created_at=now - timedelta(days=rng.randint(2, 30), hours=rng.randint(0, 23)),
            ))
            n += 1
    db.commit()
    return n


def seed_scenarios() -> list:
    async def _quiet(_payload):
        return None

    main.notify.send = _quiet  # never email anyone while seeding
    settings.demo_mode = True  # scenarios use the simulate overrides; they're stored as simulated=true
    client = TestClient(main.app)
    headers = {"X-Service-Key": settings.service_api_key}

    def send(uid, handle, to, amount, cadence=180.0, **simulate):
        r = client.post(f"/api/v1/users/{uid}/transfers", headers=headers, json={
            "recipient_id": to, "amount": amount, "device_id": f"seed-{handle}-phone",
            "cadence_ms": cadence, "simulate": simulate or None})
        if r.status_code != 200:
            sys.exit(f"Scenario transfer failed ({r.status_code}): {r.text}")
        return r.json()

    return [
        send("usr_1005", "vikram", "usr_1003", 1800),  # routine
        send("usr_1004", "ananya", "usr_1005", 30000, new_device=True),  # stays held for the SOC queue
        send("usr_1005", "vikram", "usr_9999", 40000, new_device=True, far_location=True),  # takeover, declined
    ] + [  # scripted burst: each looks harmless until velocity catches the fifth
        send("usr_1003", "rohan", "usr_9999", 2500, bot_typing=True) for _ in range(5)
    ]


def main_cli():
    if not settings.service_api_key:
        sys.exit("SERVICE_API_KEY is not set. Copy .env.example to .env (or run `python run.py`).")
    if "--reset" in sys.argv:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if db.query(User).count():
            print("Database already seeded. Use --reset to start over.")
            return
        n = seed_history(db)
    results = seed_scenarios()
    print(f"Seeded {len(CUSTOMERS)} customers, {n} historical transfers, {len(results)} live scenarios:")
    for r in results:
        print(f"  {r['id']}  {r['sender_name']:>13} -> {r['recipient_name']:<18} INR {r['amount']:>9,.2f}  "
              f"risk {r['risk_score']:.2f}  {r['status']}")


if __name__ == "__main__":
    main_cli()
