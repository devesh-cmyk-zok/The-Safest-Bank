import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# Must be set before any app module reads settings (load_dotenv never overrides these).
os.environ.update(
    DATABASE_URL=f"sqlite:///{tempfile.mkdtemp()}/test.db",
    SERVICE_API_KEY="test-key",
    DEMO_MODE="true",
    N8N_WEBHOOK_URL="",
    N8N_WEBHOOK_SECRET="",
)

import pytest  # noqa: E402

from database.connection import Base, SessionLocal, engine  # noqa: E402
from database.models import User  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def users(db):
    db.add_all([
        User(id="usr_a", full_name="Alice", email="alice@example.com", balance_paise=10_000_000),
        User(id="usr_b", full_name="Bob", email="bob@example.com", balance_paise=5_000_000),
    ])
    db.commit()
