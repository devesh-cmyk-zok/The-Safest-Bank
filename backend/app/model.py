"""Small PyTorch MLP over the six signal risks. Trained by backend/train_model.py."""

from pathlib import Path

import torch
import torch.nn as nn

from app.features import FEATURES

APP_DIR = Path(__file__).resolve().parent
WEIGHTS_PATH = APP_DIR / "fraud_model.pth"
METRICS_PATH = APP_DIR / "model_metrics.json"


class FraudMLP(nn.Module):
    def __init__(self, n_features: int = len(FEATURES)):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(n_features, 16), nn.ReLU(), nn.Dropout(0.1),
            nn.Linear(16, 8), nn.ReLU(),
            nn.Linear(8, 1),  # logit; sigmoid applied in predict()
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1)


_model = None


def _load() -> FraudMLP:
    global _model
    if _model is None:
        if not WEIGHTS_PATH.exists():
            raise RuntimeError(f"{WEIGHTS_PATH.name} missing. Run: python backend/train_model.py")
        m = FraudMLP()
        m.load_state_dict(torch.load(WEIGHTS_PATH, map_location="cpu", weights_only=True))
        m.eval()
        _model = m
    return _model


def predict(risks: dict) -> float:
    """Fraud probability in [0, 1] for one transfer's signal risks."""
    x = torch.tensor([[risks[f] for f in FEATURES]], dtype=torch.float32)
    with torch.no_grad():
        return round(float(torch.sigmoid(_load()(x)).item()), 4)
