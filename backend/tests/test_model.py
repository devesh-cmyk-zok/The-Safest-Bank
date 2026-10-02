import json
from datetime import timedelta

from app import engine, features, model
from database.models import KnownDevice, Transaction, TxStatus, utcnow

ROUTINE = features.Signals(amount_ratio=0.8, velocity_1h=0, new_payee=False, new_device=False, cadence_ms=180, distance_km=5)
TAKEOVER = features.Signals(amount_ratio=12, velocity_1h=1, new_payee=True, new_device=True, cadence_ms=150, distance_km=1800)


def test_risks_are_bounded():
    for s in (ROUTINE, TAKEOVER, features.Signals(0, 0, False, False, None, 0)):
        risks = features.risks(s)
        assert list(risks) == features.FEATURES
        assert all(0.0 <= v <= 1.0 for v in risks.values())


def test_bot_cadence_is_risky_and_human_cadence_is_not():
    assert features.cadence_risk(20) == 1.0
    assert features.cadence_risk(180) == 0.0
    assert 0 < features.cadence_risk(None) < 0.5


def test_trained_model_separates_obvious_cases():
    assert model.predict(features.risks(ROUTINE)) < 0.2
    assert model.predict(features.risks(TAKEOVER)) > 0.8


def test_metrics_file_is_honest_about_synthetic_data():
    metrics = json.loads(model.METRICS_PATH.read_text())
    assert metrics["dataset"]["kind"] == "synthetic"
    for key in ("roc_auc", "precision", "recall", "f1"):
        assert 0.0 <= metrics["ensemble"][key] <= 1.0
    assert set(metrics["feature_importance"]) == set(features.FEATURES)


def test_gather_reads_history_from_db(db, users):
    now = utcnow()
    db.add_all([
        Transaction(id=f"h{i}", user_id="usr_a", recipient_id="usr_b", amount_paise=200_000,
                    status=TxStatus.SETTLED, created_at=now - timedelta(days=i + 1))
        for i in range(5)
    ] + [
        Transaction(id="recent", user_id="usr_a", recipient_id="usr_b", amount_paise=100_000,
                    status=TxStatus.SETTLED, created_at=now - timedelta(minutes=10)),
        KnownDevice(user_id="usr_a", device_id="dev-home"),
    ])
    db.commit()

    s = features.gather(db, "usr_a", "usr_b", amount_paise=2_000_000, device_id="dev-home", cadence_ms=None, distance_km=0)
    assert s.amount_ratio == 10.0  # ₹20,000 vs ₹2,000 median
    assert s.velocity_1h == 1
    assert (s.new_payee, s.new_device) == (False, False)

    s2 = features.gather(db, "usr_a", "usr_x", amount_paise=100_000, device_id="dev-other", cadence_ms=None, distance_km=0)
    assert (s2.new_payee, s2.new_device) == (True, True)


def test_first_device_on_account_is_trusted(db, users):
    s = features.gather(db, "usr_a", "usr_b", amount_paise=100_000, device_id="dev-new", cadence_ms=None, distance_km=0)
    assert s.new_device is False  # trust on first use: no devices registered yet


def test_rule_score_uses_all_weights():
    assert abs(sum(engine.RULE_WEIGHTS.values()) - 1.0) < 1e-9
    assert set(engine.RULE_WEIGHTS) == set(features.FEATURES)
