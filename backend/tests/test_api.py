import json
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app import main
from app.config import settings
from database.models import KnownDevice, Transaction, TxStatus, User, utcnow

KEY = {"X-Service-Key": "test-key"}


@pytest.fixture
def sent(monkeypatch):
    """Captures what would be POSTed to n8n."""
    events = []

    async def fake_send(payload):
        events.append(payload)

    monkeypatch.setattr(main.notify, "send", fake_send)
    return events


@pytest.fixture
def client():
    return TestClient(main.app)


@pytest.fixture
def history(db, users):
    """Alice has paid Bob ₹2,000 ten times from her registered device."""
    now = utcnow()
    db.add_all([
        Transaction(id=f"h{i}", user_id="usr_a", recipient_id="usr_b", amount_paise=200_000,
                    status=TxStatus.SETTLED, created_at=now - timedelta(days=i + 2))
        for i in range(10)
    ] + [KnownDevice(user_id="usr_a", device_id="dev-home"),
         User(id="usr_c", full_name="Carol", email="carol@example.com", balance_paise=0)])
    db.commit()


def _transfer(client, **body):
    body = {"recipient_id": "usr_b", "amount": 2000, "device_id": "dev-home", "cadence_ms": 180, **body}
    return client.post("/api/v1/users/usr_a/transfers", json=body, headers=KEY)


def _balance(db, uid):
    db.expire_all()
    return db.get(User, uid).balance_paise


def test_every_api_route_requires_the_service_key(client, users):
    assert client.get("/api/v1/users/usr_a").status_code == 401
    assert client.get("/api/v1/users/usr_a", headers={"X-Service-Key": "wrong"}).status_code == 401
    assert client.get("/api/v1/admin/stats").status_code == 401
    assert client.post("/api/v1/users/usr_a/transfers", json={}).status_code == 401
    assert client.get("/health").status_code == 200


def test_routine_transfer_settles(client, db, history, sent):
    r = _transfer(client)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "SETTLED"
    assert (_balance(db, "usr_a"), _balance(db, "usr_b")) == (9_800_000, 5_200_000)
    assert sent == []


def test_risky_transfer_is_held_and_the_otp_only_goes_to_n8n(client, db, history, sent):
    r = _transfer(client, recipient_id="usr_c", amount=25000, simulate={"new_device": True})
    body = r.json()
    assert body["status"] == "ESCROW_HELD", body
    assert "otp" not in json.dumps(body).lower().replace("otp_attempts_left", "")
    assert _balance(db, "usr_a") == 10_000_000 - 2_500_000 and _balance(db, "usr_c") == 0

    [event] = sent
    assert event["decision"] == "ESCROW_HELD" and event["email"] == "alice@example.com"
    assert len(event["otp_code"]) == 6

    r = client.post(f"/api/v1/users/usr_a/transfers/{body['id']}/verify-otp", json={"otp": event["otp_code"]}, headers=KEY)
    assert r.status_code == 200 and r.json()["status"] == "SETTLED"
    assert _balance(db, "usr_c") == 2_500_000
    # the device that passed step-up is now trusted
    assert db.query(KnownDevice).filter_by(user_id="usr_a").count() == 2


def test_wrong_otp_counts_down_then_locks(client, history, sent):
    tx_id = _transfer(client, recipient_id="usr_c", amount=25000, simulate={"new_device": True}).json()["id"]
    wrong = "000000" if sent[0]["otp_code"] != "000000" else "111111"
    url = f"/api/v1/users/usr_a/transfers/{tx_id}/verify-otp"
    r = client.post(url, json={"otp": wrong}, headers=KEY)
    assert r.status_code == 400 and r.json()["detail"]["attempts_left"] == 4
    for _ in range(4):
        r = client.post(url, json={"otp": wrong}, headers=KEY)
    assert r.status_code == 423
    assert client.post(url, json={"otp": sent[0]["otp_code"]}, headers=KEY).status_code == 423


def test_another_customer_cannot_touch_my_transfer(client, history, sent):
    tx_id = _transfer(client, recipient_id="usr_c", amount=25000, simulate={"new_device": True}).json()["id"]
    r = client.post(f"/api/v1/users/usr_b/transfers/{tx_id}/verify-otp", json={"otp": sent[0]["otp_code"]}, headers=KEY)
    assert r.status_code == 404
    assert client.post(f"/api/v1/users/usr_b/transfers/{tx_id}/cancel", headers=KEY).status_code == 404


def test_cancel_refunds_held_transfer(client, db, history, sent):
    tx_id = _transfer(client, recipient_id="usr_c", amount=25000, simulate={"new_device": True}).json()["id"]
    r = client.post(f"/api/v1/users/usr_a/transfers/{tx_id}/cancel", headers=KEY)
    assert r.status_code == 200 and r.json()["status"] == "CANCELLED"
    assert _balance(db, "usr_a") == 10_000_000
    assert client.post(f"/api/v1/users/usr_a/transfers/{tx_id}/cancel", headers=KEY).status_code == 409


def test_takeover_pattern_is_declined_and_nothing_moves(client, db, history, sent):
    r = _transfer(client, recipient_id="usr_c", amount=25000, simulate={"new_device": True, "far_location": True})
    assert r.json()["status"] == "AUTO_ABORTED"
    assert _balance(db, "usr_a") == 10_000_000
    [event] = sent
    assert event["decision"] == "AUTO_ABORT" and "otp_code" not in event


def test_insufficient_funds(client, history, sent):
    r = _transfer(client, amount=200000)
    assert r.status_code == 400 and "Insufficient" in r.json()["detail"]


def test_bad_input_is_rejected(client, history):
    assert _transfer(client, amount=-5).status_code == 422
    assert _transfer(client, amount="10.001").status_code == 422
    assert _transfer(client, recipient_id="usr_a").status_code == 400
    assert _transfer(client, recipient_id="usr_nobody").status_code == 404


def test_simulation_is_refused_outside_demo_mode(client, history, monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", False)
    assert _transfer(client, simulate={"new_device": True}).status_code == 400


def test_soc_release_and_refund(client, db, history, sent):
    held = [_transfer(client, recipient_id="usr_c", amount=25000, simulate={"new_device": True}).json()["id"]
            for _ in range(2)]
    body = {"analyst": "analyst1", "note": "called customer"}
    r = client.post(f"/api/v1/admin/transactions/{held[0]}/release", json=body, headers=KEY)
    assert r.status_code == 200 and r.json()["resolved_by"] == "soc:analyst1"
    r = client.post(f"/api/v1/admin/transactions/{held[1]}/refund", json=body, headers=KEY)
    assert r.json()["status"] == "BLOCKED_BY_SOC"
    assert client.post(f"/api/v1/admin/transactions/{held[1]}/release", json=body, headers=KEY).status_code == 409
    assert (_balance(db, "usr_a"), _balance(db, "usr_c")) == (10_000_000 - 2_500_000, 2_500_000)


def test_customer_history_hides_other_peoples_risk_details(client, history, sent):
    _transfer(client)
    rows = client.get("/api/v1/users/usr_b/transactions", headers=KEY).json()
    incoming = [r for r in rows if r["direction"] == "in"]
    assert incoming and all("risk_score" not in r for r in incoming)


def test_admin_stats_shape(client, history, sent):
    _transfer(client)
    _transfer(client, recipient_id="usr_c", amount=25000, simulate={"new_device": True})
    stats = client.get("/api/v1/admin/stats", headers=KEY).json()
    assert stats["counts"]["ESCROW_HELD"] == 1
    assert len(stats["last_24h"]) == 24
    assert {"signal": "new_device", "count": 1} in stats["top_signals"]


def test_admin_model_reports_metrics_and_policy(client):
    body = client.get("/api/v1/admin/model", headers=KEY).json()
    assert body["dataset"]["kind"] == "synthetic"
    assert body["policy"]["hold_at"] == 0.6 and body["policy"]["abort_at"] == 0.85
