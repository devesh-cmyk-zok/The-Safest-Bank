"""Environment-driven settings. Both servers read the repo-root .env."""

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR.parent / ".env")


def _flag(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    def __init__(self) -> None:
        self.service_api_key = os.getenv("SERVICE_API_KEY", "")
        self.database_url = os.getenv("DATABASE_URL") or f"sqlite:///{BACKEND_DIR / 'safest_bank.db'}"
        self.demo_mode = _flag("DEMO_MODE")
        self.n8n_webhook_url = os.getenv("N8N_WEBHOOK_URL", "")
        self.n8n_webhook_secret = os.getenv("N8N_WEBHOOK_SECRET", "")


settings = Settings()
