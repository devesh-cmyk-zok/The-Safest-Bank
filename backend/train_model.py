"""Train the fraud MLP on seeded synthetic data and write honest held-out metrics.

    python backend/train_model.py

There is no public dataset with these exact signals, so transfers are simulated from
documented fraud patterns. The metrics describe how well the model separates *this*
synthetic distribution, not real-world performance, and model_metrics.json says so.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import engine  # noqa: E402
from app.features import FEATURES, Signals, risks  # noqa: E402
from app.model import METRICS_PATH, WEIGHTS_PATH, FraudMLP  # noqa: E402

SEED = 7
N = 30_000
FRAUD_RATE = 0.10
LABEL_NOISE = 0.015  # real labels are noisy (chargebacks disputed, fraud missed)
PATTERNS = ["account_takeover", "scripted_bot", "coached_victim", "mule_burst"]


def _cadence(rng, human=True):
    if rng.random() < 0.2:
        return None
    return float(max(60.0, rng.normal(190, 60))) if human else float(rng.uniform(8, 40))


def _legit(rng) -> Signals:
    ratio = rng.lognormal(0, 0.7) if rng.random() > 0.05 else rng.uniform(3, 15)  # rent, a big purchase
    cadence = _cadence(rng)
    if rng.random() < 0.03:
        cadence = float(rng.uniform(1500, 3000))  # slow typists exist
    r = rng.random()
    distance = rng.uniform(0, 30) if r < 0.90 else rng.uniform(30, 300) if r < 0.98 else rng.uniform(300, 2500)
    return Signals(ratio, int(rng.poisson(0.4)), rng.random() < 0.2, rng.random() < 0.05, cadence, distance)


def _fraud(rng, pattern: str) -> Signals:
    if pattern == "account_takeover":  # stolen credentials, attacker's device, drain to a new payee
        return Signals(rng.lognormal(np.log(8), 0.6), int(rng.poisson(1)), rng.random() < 0.9, rng.random() < 0.9,
                       _cadence(rng), rng.uniform(300, 3000) if rng.random() < 0.5 else rng.uniform(0, 50))
    if pattern == "scripted_bot":  # automated submissions
        return Signals(rng.lognormal(np.log(2), 0.5), int(rng.poisson(4)) + 2, rng.random() < 0.7, rng.random() < 0.5,
                       _cadence(rng, human=False) or 20.0, rng.uniform(0, 500))
    if pattern == "coached_victim":  # authorised push payment scam on the victim's own phone
        cadence = float(rng.uniform(1500, 4000)) if rng.random() < 0.6 else _cadence(rng)
        return Signals(rng.lognormal(np.log(12), 0.5), int(rng.poisson(0.5)), rng.random() < 0.95, rng.random() < 0.05,
                       cadence, rng.uniform(0, 30))
    # mule_burst: many small transfers to fresh accounts
    return Signals(rng.lognormal(np.log(0.8), 0.5), int(rng.poisson(5)) + 3, rng.random() < 0.8, rng.random() < 0.3,
                   _cadence(rng), rng.uniform(0, 100))


def make_dataset(n: int, rng):
    rows, labels, kinds = [], [], []
    for _ in range(n):
        if rng.random() < FRAUD_RATE:
            kind = PATTERNS[rng.integers(len(PATTERNS))]
            sig, y = _fraud(rng, kind), 1
        else:
            kind, sig, y = "legit", _legit(rng), 0
        if rng.random() < LABEL_NOISE:
            y = 1 - y
        r = risks(sig)
        rows.append([r[f] for f in FEATURES])
        labels.append(y)
        kinds.append(kind)
    return np.array(rows, dtype=np.float32), np.array(labels, dtype=np.float32), np.array(kinds)


def roc_auc(y, scores) -> float:
    """Probability a random fraud outranks a random legit transfer (ties count half)."""
    pos, neg = scores[y == 1], scores[y == 0]
    greater = (pos[:, None] > neg[None, :]).sum()
    ties = (pos[:, None] == neg[None, :]).sum()
    return float((greater + 0.5 * ties) / (len(pos) * len(neg)))


def at_threshold(y, scores, t) -> dict:
    pred = scores >= t
    tp, fp = int((pred & (y == 1)).sum()), int((pred & (y == 0)).sum())
    fn, tn = int((~pred & (y == 1)).sum()), int((~pred & (y == 0)).sum())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"accuracy": (tp + tn) / len(y), "precision": precision, "recall": recall, "f1": f1,
            "false_positive_rate": fp / (fp + tn) if fp + tn else 0.0,
            "confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn}}


def main():
    rng = np.random.default_rng(SEED)
    torch.manual_seed(SEED)
    X, y, kinds = make_dataset(N, rng)

    # Stratified 80/20 split.
    idx_pos, idx_neg = rng.permutation(np.where(y == 1)[0]), rng.permutation(np.where(y == 0)[0])
    cut_p, cut_n = int(0.8 * len(idx_pos)), int(0.8 * len(idx_neg))
    train = np.concatenate([idx_pos[:cut_p], idx_neg[:cut_n]])
    test = np.concatenate([idx_pos[cut_p:], idx_neg[cut_n:]])

    net = FraudMLP()
    opt = torch.optim.Adam(net.parameters(), lr=5e-3)
    loss_fn = nn.BCEWithLogitsLoss()  # unweighted: keeps probabilities calibrated to the base rate
    Xt, yt = torch.from_numpy(X[train]), torch.from_numpy(y[train])
    for _ in range(40):
        net.train()
        for batch in torch.randperm(len(train)).split(256):
            opt.zero_grad()
            loss_fn(net(Xt[batch]), yt[batch]).backward()
            opt.step()
    net.eval()

    def nn_scores(features):
        with torch.no_grad():
            return torch.sigmoid(net(torch.from_numpy(features))).numpy()

    X_test, y_test = X[test], y[test]
    nn_s = nn_scores(X_test)
    rule_s = np.array([engine.rule_score(dict(zip(FEATURES, row))) for row in X_test])
    ens = engine.NN_WEIGHT * nn_s + (1 - engine.NN_WEIGHT) * rule_s

    importance = {}
    base_auc = roc_auc(y_test, nn_s)
    for i, f in enumerate(FEATURES):
        shuffled = X_test.copy()
        shuffled[:, i] = rng.permutation(shuffled[:, i])
        importance[f] = round(base_auc - roc_auc(y_test, nn_scores(shuffled)), 4)

    kinds_test = kinds[test]
    per_pattern = {
        k: round(float((ens[(kinds_test == k) & (y_test == 1)] >= engine.HOLD_AT).mean()), 3)
        for k in PATTERNS
    }
    metrics = {
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dataset": {"kind": "synthetic", "seed": SEED, "train": int(len(train)), "test": int(len(test)),
                    "fraud_rate": FRAUD_RATE, "label_noise": LABEL_NOISE, "patterns": PATTERNS},
        "model": {"type": "MLP 6-16-8-1 (PyTorch)", "features": FEATURES},
        "threshold": engine.HOLD_AT,
        "roc_auc": {"rules_only": round(roc_auc(y_test, rule_s), 4), "neural_net": round(base_auc, 4),
                    "ensemble": round(roc_auc(y_test, ens), 4)},
        "ensemble": {"roc_auc": round(roc_auc(y_test, ens), 4),
                     **{k: (round(v, 4) if isinstance(v, float) else v)
                        for k, v in at_threshold(y_test, ens, engine.HOLD_AT).items()}},
        "recall_by_pattern": per_pattern,
        "feature_importance": dict(sorted(importance.items(), key=lambda kv: kv[1], reverse=True)),
    }

    torch.save(net.state_dict(), WEIGHTS_PATH)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2) + "\n")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
