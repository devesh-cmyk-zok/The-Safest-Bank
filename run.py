"""Run The Safest Bank locally with one command.

    python run.py                 # set up on first run, then start engine (:8001) + portal/SOC (:8000)
    python run.py test            # run the engine and Django test suites
    python run.py seed --reset    # wipe and reseed the demo data

First run creates .env from .env.example with fresh random keys, trains the model if the
weights are missing, creates the databases and seeds demo customers.
"""

import os
import secrets
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
PY = sys.executable


def ensure_env() -> None:
    env = ROOT / ".env"
    if env.exists():
        return
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    text = text.replace("SERVICE_API_KEY=change-me", f"SERVICE_API_KEY={secrets.token_urlsafe(32)}", 1)
    text = text.replace("DJANGO_SECRET_KEY=change-me", f"DJANGO_SECRET_KEY={secrets.token_urlsafe(50)}", 1)
    env.write_text(text, encoding="utf-8")
    print("Created .env with fresh random keys.")


def run(*args: str, cwd: Path = ROOT) -> None:
    subprocess.run([PY, *args], cwd=cwd, check=True)


def seed(*extra: str) -> None:
    run("backend/seed.py", *extra)
    run("manage.py", "migrate", "-v0", cwd=FRONTEND)
    run("manage.py", "seed_demo", cwd=FRONTEND)


def serve() -> None:
    ensure_env()
    if not (BACKEND / "app" / "fraud_model.pth").exists():
        run("backend/train_model.py")
    seed()
    procs = [
        subprocess.Popen([PY, "-m", "uvicorn", "app.main:app", "--port", "8001"], cwd=BACKEND),
        # --noreload: the autoreloader's child process would outlive a terminate() on Windows.
        subprocess.Popen([PY, "manage.py", "runserver", "8000", "--noreload"], cwd=FRONTEND),
    ]
    print("\n  Portal + SOC     http://127.0.0.1:8000   (aarav / demo123 · analyst / demo123)"
          "\n  Engine API docs  http://127.0.0.1:8001/docs   (needs X-Service-Key)\n  Ctrl+C to stop.\n")
    try:
        while all(p.poll() is None for p in procs):
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        for p in procs:
            p.terminate()
        for p in procs:
            p.wait()


def test() -> None:
    env = {**os.environ, "DEBUG": os.environ.get("DEBUG", "true")}  # Django needs a key or DEBUG
    code = subprocess.call([PY, "-m", "pytest", "-q", "backend/tests"], cwd=ROOT)
    code |= subprocess.call([PY, "manage.py", "test"], cwd=FRONTEND, env=env)
    sys.exit(code)


if __name__ == "__main__":
    command, *rest = sys.argv[1:] or ["serve"]
    if command == "test":
        test()
    elif command == "seed":
        ensure_env()
        seed(*rest)
    elif command == "serve":
        serve()
    else:
        sys.exit(__doc__)
