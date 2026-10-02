import asyncio
from datetime import timedelta

import httpx

from app import notify, otp
from app.config import settings
from database.models import Transaction, TxStatus, utcnow


def _held(db):
    tx = Transaction(id="tx_h", user_id="usr_a", recipient_id="usr_b", amount_paise=100, status=TxStatus.ESCROW_HELD)
    db.add(tx)
    db.commit()
    return tx


def test_code_is_six_digits_and_not_stored_in_clear(db, users):
    tx = _held(db)
    code = otp.issue(tx)
    db.commit()
    assert len(code) == 6 and code.isdigit()
    assert code not in (tx.otp_hash or "")


def test_correct_code_passes(db, users):
    tx = _held(db)
    code = otp.issue(tx)
    db.commit()
    assert otp.check(db, tx, code) == "ok"


def test_five_wrong_codes_lock_it_even_for_the_right_code(db, users):
    tx = _held(db)
    code = otp.issue(tx)
    db.commit()
    wrong = "000000" if code != "000000" else "111111"
    results = [otp.check(db, tx, wrong) for _ in range(otp.MAX_ATTEMPTS)]
    assert results == ["invalid"] * (otp.MAX_ATTEMPTS - 1) + ["locked"]
    assert otp.check(db, tx, code) == "locked"


def test_expired_code_fails(db, users):
    tx = _held(db)
    code = otp.issue(tx)
    tx.otp_expires_at = utcnow() - timedelta(seconds=1)
    db.commit()
    assert otp.check(db, tx, code) == "expired"


def test_notify_posts_payload_with_secret_header(monkeypatch):
    seen = {}

    def handler(request):
        seen["body"] = request.content
        seen["secret"] = request.headers.get("X-Webhook-Secret")
        return httpx.Response(200)

    monkeypatch.setattr(settings, "n8n_webhook_url", "http://n8n.test/webhook/fraud-alert")
    monkeypatch.setattr(settings, "n8n_webhook_secret", "s3cret")
    monkeypatch.setattr(notify, "_transport", httpx.MockTransport(handler))
    asyncio.run(notify.send({"transaction_id": "tx_1", "decision": "ESCROW_HELD", "otp_code": "123456"}))
    assert seen["secret"] == "s3cret" and b'"otp_code":"123456"' in seen["body"].replace(b" ", b"")


def test_notify_failure_is_swallowed(monkeypatch):
    monkeypatch.setattr(settings, "n8n_webhook_url", "http://n8n.test/webhook/fraud-alert")
    monkeypatch.setattr(notify, "_transport", httpx.MockTransport(lambda r: httpx.Response(500)))
    asyncio.run(notify.send({"transaction_id": "tx_1"}))  # must not raise
