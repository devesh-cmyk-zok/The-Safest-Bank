from app import engine, pipeline
from database.models import TxStatus

LOW = {"amount_ratio": 0.0, "velocity_1h": 0.0, "new_payee": 0.0, "new_device": 0.0, "cadence": 0.0, "distance": 0.0}
HOLD = {**LOW, "amount_ratio": 0.77, "new_payee": 1.0, "new_device": 1.0}
ABORT = {**HOLD, "distance": 1.0}


def test_decide_thresholds():
    assert engine.decide(0.5999) == TxStatus.SETTLED
    assert engine.decide(0.60) == TxStatus.ESCROW_HELD
    assert engine.decide(0.8499) == TxStatus.ESCROW_HELD
    assert engine.decide(0.85) == TxStatus.AUTO_ABORTED


def test_low_risk_settles_with_no_reasons():
    out = pipeline.run(LOW, amount_paise=250_000)
    assert out["status"] == TxStatus.SETTLED
    assert out["reasons"] == []
    assert out["soc_report"]["severity"] == "LOW"


def test_held_transfer_explains_itself_in_rupees():
    out = pipeline.run(HOLD, amount_paise=2_500_000)
    assert out["status"] == TxStatus.ESCROW_HELD
    assert out["reasons"][0] == engine.LABELS["amount_ratio"]  # biggest contribution first
    assert "₹25,000.00" in out["user_message"] and "$" not in out["user_message"]
    assert out["soc_report"]["severity"] == "HIGH"


def test_abort_is_critical():
    out = pipeline.run(ABORT, amount_paise=2_500_000)
    assert out["status"] == TxStatus.AUTO_ABORTED
    assert out["soc_report"]["severity"] == "CRITICAL"


def test_inr_uses_indian_grouping():
    assert pipeline.inr(1_00_00_000_00) == "₹1,00,00,000.00"
    assert pipeline.inr(123_456_78) == "₹1,23,456.78"
    assert pipeline.inr(5_00) == "₹5.00"
