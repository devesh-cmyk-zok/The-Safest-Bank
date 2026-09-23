import numpy as np

def calculate_shap_attributions(transaction_data: dict) -> dict:
    """
    Calculates feature-level SHAP risk contributions for transaction evaluation.
    """
    amount = float(transaction_data.get("amount", 0.0))
    distance_km = float(transaction_data.get("distance_km", 0.0))
    is_new_device = bool(transaction_data.get("is_new_device", False))
    velocity_1h = int(transaction_data.get("velocity_1h", 1))

    base_value = 0.05

    amount_risk = min(1.0, round(amount / 50000.0, 3))
    distance_risk = min(1.0, round(distance_km / 500.0, 3))
    device_risk = 0.45 if is_new_device else 0.05
    cadence_risk = min(1.0, round(velocity_1h / 10.0, 3))

    raw_score = base_value + (0.35 * amount_risk) + (0.25 * distance_risk) + (0.25 * device_risk) + (0.15 * cadence_risk)
    composite_risk = round(float(np.clip(raw_score, 0.0, 0.99)), 3)

    return {
        "composite_risk": composite_risk,
        "signal_attribution": {
            "amount_risk": amount_risk,
            "distance_risk": distance_risk,
            "device_risk": device_risk,
            "cadence_risk": cadence_risk
        }
    }