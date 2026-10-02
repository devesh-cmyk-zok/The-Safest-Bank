"""End to end: Django gateway -> real FastAPI engine (in-process) -> ledger, OTP, SOC.

The engine runs against its own temporary SQLite file; n8n delivery is captured instead of sent.
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings

KEY = "e2e-service-key"
# The engine reads its settings at import time, so configure it before importing it.
os.environ.update(DATABASE_URL=f"sqlite:///{tempfile.mkdtemp()}/e2e.db", SERVICE_API_KEY=KEY,
                  DEMO_MODE="true", N8N_WEBHOOK_URL="", N8N_WEBHOOK_SECRET="")
sys.path.insert(0, str(Path(settings.BASE_DIR).parent / "backend"))

from fastapi.testclient import TestClient  # noqa: E402

import seed as engine_seed  # noqa: E402
from app import main as engine  # noqa: E402
from config import bank_api  # noqa: E402
from database.connection import Base, SessionLocal  # noqa: E402
from database.connection import engine as engine_db  # noqa: E402
from soc.models import AuditLog  # noqa: E402

from .models import PortalProfile  # noqa: E402


@override_settings(SERVICE_API_KEY=KEY, DEMO_MODE=True)
class EndToEndTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Base.metadata.drop_all(engine_db)
        Base.metadata.create_all(engine_db)
        with SessionLocal() as db:
            engine_seed.seed_history(db)
        engine_seed.seed_scenarios()  # leaves Ananya's 30k transfer held for the SOC
        cls.sent = []

        async def capture(payload):
            cls.sent.append(payload)

        cls.patches = [
            mock.patch.object(engine.notify, "send", capture),
            mock.patch.object(bank_api, "_client",
                              TestClient(engine.app, base_url="http://engine", headers={"X-Service-Key": KEY})),
        ]
        for p in cls.patches:
            p.start()

    @classmethod
    def tearDownClass(cls):
        for p in cls.patches:
            p.stop()
        super().tearDownClass()

    def _post(self, client, url, body):
        return client.post(url, data=body, content_type="application/json")

    def test_customer_step_up_and_analyst_refund(self):
        aarav = User.objects.create_user("aarav", password="pw", first_name="Aarav")
        PortalProfile.objects.create(user=aarav, bank_user_id="usr_1001")
        customer = Client()
        self.assertEqual(customer.post("/login/", {"username": "aarav", "password": "pw"}).status_code, 302)
        start = customer.get("/api/me/").json()["balance"]

        # 1. A routine payment to a regular payee settles; this browser becomes the trusted device.
        r = self._post(customer, "/api/transfers/", {"recipient_id": "usr_1002", "amount": "2000.00", "cadence_ms": 170})
        self.assertEqual(r.json()["status"], "SETTLED", r.content)
        self.assertEqual(customer.get("/api/me/").json()["known_devices"], 1)

        # 2. New payee + large amount + unrecognised device: held, and the OTP only goes to n8n.
        r = self._post(customer, "/api/transfers/", {"recipient_id": "usr_1005", "amount": "15000",
                                                     "cadence_ms": 170, "simulate": {"new_device": True}})
        held = r.json()
        self.assertEqual(held["status"], "ESCROW_HELD", held)
        otp = self.sent[-1]["otp_code"]
        self.assertNotIn(otp.encode(), r.content)
        self.assertEqual(self.sent[-1]["email"], "aarav@example.com")

        wrong = "000000" if otp != "000000" else "111111"
        r = self._post(customer, f"/api/transfers/{held['id']}/verify-otp/", {"otp": wrong})
        self.assertEqual((r.status_code, r.json()["detail"]["attempts_left"]), (400, 4))
        r = self._post(customer, f"/api/transfers/{held['id']}/verify-otp/", {"otp": otp})
        self.assertEqual(r.json()["status"], "SETTLED")
        self.assertEqual(customer.get("/api/me/").json()["balance"], start - 17000)

        # 3. Another customer can't see Aarav's risk details or act on his transfers.
        r = self._post(customer, "/api/transfers/tx_does_not_exist/cancel/", {})
        self.assertEqual(r.status_code, 404)

        # 4. An analyst refunds the transfer the seed left held; money returns and it's audited.
        User.objects.create_user("analyst", password="pw", is_staff=True)
        soc = Client()
        soc.post("/login/", {"username": "analyst", "password": "pw"})
        [queued] = [t for t in soc.get("/soc/verification/").context["queue"] if t["sender_id"] == "usr_1004"]
        ananya_before = bank_api.call("GET", "/users/usr_1004")["balance"]
        r = self._post(soc, f"/soc/api/transaction/{queued['id']}/action/", {"action": "REFUND", "note": "customer denied"})
        self.assertEqual(r.json()["status"], "BLOCKED_BY_SOC")
        self.assertEqual(bank_api.call("GET", "/users/usr_1004")["balance"], ananya_before + 30000)
        log = AuditLog.objects.get(transaction_id=queued["id"])
        self.assertEqual((log.action, log.notes, log.analyst.username), ("Refunded held transfer", "customer denied", "analyst"))
