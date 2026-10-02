import json
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase

from config.bank_api import BankAPIError

from .models import AuditLog, SecurityCase

HELD = {
    "id": "tx_held1", "sender_id": "usr_1001", "sender_name": "Aarav Sharma", "recipient_id": "usr_9999",
    "recipient_name": "=HYPERLINK(\"http://evil\")", "amount": 25000.0, "status": "ESCROW_HELD",
    "created_at": "2026-09-23T10:00:00+00:00", "resolved_at": None, "risk_score": 0.77, "nn_score": 0.9,
    "rule_score": 0.58, "reasons": ["Unrecognised device"], "contributions": {"new_device": 0.2, "cadence": 0.0},
    "severity": "HIGH", "user_message": "", "simulated": True, "resolved_by": None, "resolution_note": None,
    "otp_attempts_left": 5, "signals": {"amount_ratio": 12.5, "velocity_1h": 0, "new_payee": True, "new_device": True,
                                        "cadence_ms": None, "distance_km": 0, "risks": {"amount_ratio": 0.84}},
    "soc_report": {},
}
STATS = {
    "total": 3, "counts": {"SETTLED": 2, "ESCROW_HELD": 1, "AUTO_ABORTED": 0, "CANCELLED": 0, "BLOCKED_BY_SOC": 0},
    "volume": {"SETTLED": 4000.0, "ESCROW_HELD": 25000.0, "AUTO_ABORTED": 0, "CANCELLED": 0, "BLOCKED_BY_SOC": 0},
    "flag_rate": 0.3333, "avg_risk": 0.3, "risk_bands": {"low": 2, "medium": 0, "high": 1, "critical": 0},
    "top_signals": [{"signal": "new_device", "count": 1}], "resolution": {}, "mean_time_to_resolve_s": None,
    "last_24h": [{"hour": f"2026-09-23T{h:02d}:00:00+00:00", "total": 1, "flagged": 0} for h in range(24)],
    "simulated": 1,
}


def fake_engine(method, path, **kwargs):
    if path == "/admin/stats":
        return STATS
    if path == "/admin/transactions":
        return [HELD]
    if path == "/admin/transactions/tx_held1":
        return HELD
    if path.endswith("/release"):
        return {**HELD, "status": "SETTLED", "resolved_by": "soc:analyst"}
    if path == "/admin/users":
        return [{"user_id": "usr_1001", "full_name": "Aarav Sharma", "email": "a@example.com", "balance": 1.0,
                 "transactions": 1, "flagged": 1, "held": 1, "max_risk": 0.77, "known_devices": 1, "watch": True}]
    raise AssertionError(f"unexpected engine call {method} {path}")


@mock.patch("config.bank_api.call", side_effect=fake_engine)
class SocTests(TestCase):
    def setUp(self):
        self.analyst = User.objects.create_user("analyst", password="x", is_staff=True)
        self.client.force_login(self.analyst)

    def _action(self, action, note="checked"):
        return self.client.post("/soc/api/transaction/tx_held1/action/",
                                data=json.dumps({"action": action, "note": note}), content_type="application/json")

    def test_pages_render_from_engine_data(self, call):
        for url in ["/soc/", "/soc/transactions/", "/soc/alerts/", "/soc/verification/",
                    "/soc/analytics/", "/soc/users-accounts/", "/soc/cases/", "/soc/audit-logs/", "/soc/reports/"]:
            r = self.client.get(url)
            self.assertEqual(r.status_code, 200, url)
        self.assertContains(self.client.get("/soc/verification/"), "tx_held1")

    def test_release_calls_engine_and_is_audited(self, call):
        r = self._action("RELEASE")
        self.assertEqual(r.json()["status"], "SETTLED")
        call.assert_any_call("POST", "/admin/transactions/tx_held1/release", json={"analyst": "analyst", "note": "checked"})
        log = AuditLog.objects.get()
        self.assertEqual((log.action, log.transaction_id, log.analyst, log.result),
                         ("Released held transfer", "tx_held1", self.analyst, "Successful"))

    def test_failed_action_is_audited_as_failed(self, call):
        call.side_effect = BankAPIError(409, "Transfer is SETTLED, not held")
        r = self._action("REFUND")
        self.assertEqual(r.status_code, 409)
        self.assertEqual(AuditLog.objects.get().result, "Failed")

    def test_open_case_from_transaction(self, call):
        r = self._action("CASE", note="")
        case = SecurityCase.objects.get()
        self.assertEqual(r.json()["case_id"], case.case_id)
        self.assertEqual((case.account, case.transaction_id, case.severity), ("usr_1001", "tx_held1", "HIGH"))

    def test_csv_export_neutralises_formulas_and_is_audited(self, call):
        r = self.client.get("/soc/reports/transactions.csv")
        body = r.content.decode()
        self.assertIn("'=HYPERLINK", body)
        self.assertEqual(AuditLog.objects.get().action, "Exported transactions CSV")

    def test_engine_down_shows_502_page(self, call):
        call.side_effect = BankAPIError(503, "The fraud engine is unreachable.")
        r = self.client.get("/soc/")
        self.assertEqual(r.status_code, 502)
        self.assertContains(r, "unreachable", status_code=502)


class SocAccessTests(TestCase):
    def test_customer_gets_403(self):
        self.client.force_login(User.objects.create_user("aarav", password="x"))
        self.assertEqual(self.client.get("/soc/").status_code, 403)
        r = self.client.post("/soc/api/transaction/tx_1/action/", data="{}", content_type="application/json")
        self.assertEqual(r.status_code, 403)

    def test_anonymous_redirects_to_login(self):
        self.assertRedirects(self.client.get("/soc/"), "/login/?next=/soc/", fetch_redirect_response=False)
