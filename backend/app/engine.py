"""
FILE: app/engine.py
PURPOSE:
    Hybrid fraud evaluation engine combining heuristic telemetry checks 
    with PyTorch neural inference.
"""

from typing import Dict, Any, Tuple
from database.models import EscrowStatus
from app.pytorch_model import predict_fraud_risk


class FraudScoringEngine:
    def __init__(self):
        # Baseline heuristic weights for multi-factor risk estimation
        self.w_amount = 0.25
        self.w_cadence = 0.25
        self.w_distance = 0.30
        self.w_device = 0.20

    def evaluate_transaction(
        self, 
        amount: float, 
        delta_t_ms: int, 
        ip_distance_km: float, 
        device_hash: str
    ) -> Tuple[float, EscrowStatus, Dict[str, Any]]:
        factors = {}
        
        # 1. Amount anomaly factor (calibrated for standard daily retail volume)
        # 1. Amount anomaly factor (calibrated for standard daily testing)
        if amount >= 15000.0:
            amount_risk = 0.90  # Large transfer relative to account size
        elif amount >= 8000.0:
            amount_risk = 0.60
        elif amount >= 3000.0:
            amount_risk = 0.35
        else:
            amount_risk = 0.05
        factors["amount_risk"] = round(amount_risk, 3)

        # 2. Behavioral keystroke cadence factor
        # Sub-35ms indicates automated script/bot; >1200ms suggests hesitation/distraction
        if delta_t_ms < 35:
            cadence_risk = 0.95  # Probable bot automation
        elif delta_t_ms > 1200:
            cadence_risk = 0.60  # High hesitation / manual entry coercion
        elif 80 <= delta_t_ms <= 300:
            cadence_risk = 0.05  # Natural human keystroke window
        else:
            cadence_risk = 0.30
        factors["cadence_risk"] = round(cadence_risk, 3)

        # 3. Geolocation variance factor
        if ip_distance_km > 1000.0:
            distance_risk = 0.90  # Impossible travel / overseas proxy
        elif ip_distance_km > 250.0:
            distance_risk = 0.50  # Inter-state travel anomaly
        else:
            distance_risk = 0.05  # Routine regional radius
        factors["distance_risk"] = round(distance_risk, 3)

        # 4. Device integrity factor (mock check against trusted ledger)
        trusted_hashes = {"a9f4c3d2e1b0", "trusted_dev_primary"}
        is_trusted = device_hash in trusted_hashes
        device_risk = 0.05 if is_trusted else 0.65
        factors["device_risk"] = round(device_risk, 3)

        # 5. Rule-Based Heuristic Score
        heuristic_score = (
            (amount_risk * self.w_amount) +
            (cadence_risk * self.w_cadence) +
            (distance_risk * self.w_distance) +
            (device_risk * self.w_device)
        )
        heuristic_score = round(min(1.0, max(0.0, heuristic_score)), 3)

        # 6. PyTorch Deep Neural Network Inference
        nn_score = predict_fraud_risk(
            amount=amount,
            delta_t_ms=float(delta_t_ms),
            ip_distance_km=float(ip_distance_km),
            device_trusted=is_trusted
        )

        # 7. Ensemble Composite Score (60% PyTorch NN + 40% Heuristic Safeguards)
        composite_score = round((0.60 * nn_score) + (0.40 * heuristic_score), 3)

        # 8. Escrow Policy Routing (Tiered Architecture)
        # Score >= 0.60: High-risk anomaly -> Detain funds in escrow quarantine
        # Score < 0.60: Low/Medium risk -> Settle transaction
        if composite_score >= 0.60:
            status = EscrowStatus.ESCROW_HELD
        else:
            status = EscrowStatus.SETTLED

        # 9. Explainable AI (XAI) Telemetry Package
        xai_breakdown = {
            "composite_score": composite_score,
            "neural_score": nn_score,
            "heuristic_score": heuristic_score,
            "signal_attribution": factors,
            "quarantine_triggered": status == EscrowStatus.ESCROW_HELD
        }

        # Demo-reliable high-value hold so Send Money → OTP always triggers for large transfers
        if amount >= 100000.0:
            composite_score = max(composite_score, 0.82)
            status = EscrowStatus.ESCROW_HELD
            xai_breakdown["composite_score"] = composite_score
            xai_breakdown["quarantine_triggered"] = True
            xai_breakdown["demo_policy"] = "high_value_escrow_hold"

        return composite_score, status, xai_breakdown


risk_engine = FraudScoringEngine()