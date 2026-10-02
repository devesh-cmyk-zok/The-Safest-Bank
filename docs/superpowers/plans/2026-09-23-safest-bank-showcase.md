# Safest Bank Showcase Overhaul — Implementation Plan

> Spec: `docs/superpowers/specs/2026-09-23-safest-bank-showcase-design.md`.
> Executed inline (user asked to start building); tasks list files, interfaces and the tests that gate them.

**Goal:** honest, secure, runnable fraud-detection banking demo.
**Architecture:** Browser → Django (session/CSRF) → FastAPI (X-Service-Key) → SQLite; FastAPI → n8n (OTP email / SOC alert).
**Stack:** Python 3.12, FastAPI, SQLAlchemy 2, LangGraph, PyTorch (CPU), Django 5/6, httpx, pytest.

## Global constraints
- Money is integer paise in the DB; the API accepts and returns rupees (2dp).
- OTP never appears in any HTTP response. No universal OTP.
- Every FastAPI `/api/*` route requires `X-Service-Key`; `/health` is public.
- Django takes the acting user from the session only.
- No user-supplied string goes into `innerHTML`.
- Config comes from the root `.env` (`.env.example` committed). DEMO_MODE gates the simulate panel and console OTP.
- Delete dead code instead of commenting it out.

## Task 1 — Repo hygiene + config
Files: `requirements.txt` (root, UTF-8), `.env.example`, delete `backend/requirements.txt`, `frontend/requirements.txt`; `backend/app/config.py`.
Interface: `config.settings` with `service_api_key`, `demo_mode`, `n8n_webhook_url`, `n8n_webhook_secret`, `database_url`.
Check: `pip install -r requirements.txt` succeeds.

## Task 2 — DB models + ledger
Files: `backend/database/{connection,models}.py`, `backend/app/ledger.py`, `backend/tests/test_ledger.py`.
Models: `User(id, full_name, email, balance_paise, created_at)`, `Transaction(id, user_id, recipient_id, amount_paise, status, risk_score, decision_detail JSON, features JSON, simulated, device_id, otp_hash, otp_expires_at, otp_attempts, created_at, resolved_at, resolved_by, resolution_note)`, `KnownDevice(user_id, device_id, first_seen)`.
Status: `SETTLED, ESCROW_HELD, AUTO_ABORTED, CANCELLED, BLOCKED_BY_SOC`.
Interface (ledger): `debit(db, user_id, paise) -> bool` (atomic, conditional), `credit(db, user_id, paise)`, `transition(db, tx_id, from_status, to_status) -> bool` (compare-and-set),
`settle_held(db, tx, by, note) -> bool`, `refund_held(db, tx, to_status, by, note) -> bool`.
Tests: debit fails on insufficient funds; double settle only credits once; refund restores sender; total money conserved.

## Task 3 — Features + model + training
Files: `backend/app/features.py`, `backend/app/model.py`, `backend/train_model.py`, `backend/app/fraud_model.pth`, `backend/app/model_metrics.json`, `backend/tests/test_model.py`.
Interface: `FEATURES = ["amount_ratio","velocity_1h","new_payee","new_device","cadence","distance"]`; `RawSignals` dataclass; `compute_signals(db, user_id, recipient_id, amount_paise, device_id, cadence_ms, distance_km) -> RawSignals`;
`signal_risks(raw) -> dict[str,float]` (each in [0,1]); `model.predict(risks) -> float`.
Training: seeded synthetic legit + 4 fraud patterns, 80/20 stratified split, BCEWithLogits + pos_weight, metrics (acc/prec/rec/F1/ROC-AUC at the production threshold, rules-only vs NN vs ensemble AUC, permutation importance).
Tests: account-takeover pattern > 0.8, routine payment < 0.3, metrics JSON has the keys.

## Task 4 — Engine + LangGraph pipeline
Files: `backend/app/engine.py` (rules, contributions, decision), `backend/app/pipeline.py` (graph), delete `app/langgraph_agents.py`, `services/shap_engine.py`, `app/pytorch_model.py`.
Interface: `assess(risks: dict, amount_paise) -> dict` returns `{risk_score, rule_score, nn_score, decision, contributions, reasons, severity, soc_report, user_message}` via `pipeline.run(...)`.
Thresholds: ≥0.85 AUTO_ABORT, ≥0.60 ESCROW_HELD. Messages use ₹.
Tests: threshold boundaries; reasons ordered by contribution; message contains ₹.

## Task 5 — OTP + n8n notify
Files: `backend/app/otp.py`, `backend/app/notify.py`, delete `services/`, `app/webhook.py`; `backend/tests/test_otp.py`.
Interface: `otp.issue(tx) -> str` (sets hash/expiry/attempts on the row); `otp.check(tx, code) -> "ok"|"invalid"|"expired"|"locked"`; `notify.send(payload: dict)` async (header secret; DEMO_MODE console fallback).
Tests: correct code ok once; 5 wrong → locked, correct after lock fails; expired fails.

## Task 6 — FastAPI routes + auth
Files: `backend/app/main.py`, `backend/app/schemas.py`, `backend/tests/test_api.py`, `backend/tests/conftest.py`.
Routes: listed in spec §1. Tests: 401 without key; transfer settles for known payee/device; held transfer response has no OTP and notify payload has one; verify OTP settles and trusts the device; wrong user can't verify; cancel refunds; AUTO_ABORT refunds; admin release/refund; simulate rejected when DEMO_MODE off.

## Task 7 — Seed
File: `backend/seed.py` (`--reset`). 5 customers + mule, 30 days of settled history, a few scenario transfers through the real pipeline (simulated=true, no notify).

## Task 8 — Django gateway + auth
Files: `frontend/config/settings.py`, `frontend/config/bank_api.py`, `frontend/portal/{models,views,urls}.py`, `portal/migrations/0001_initial.py`, `portal/management/commands/seed_demo.py`, `frontend/portal/tests.py`.
Tests: gateway transfer passes the session user id (ignores body user_id); CSRF required; unauthenticated → 401/redirect; staff login redirects to /soc/.

## Task 9 — Portal UI rewire
Files: `portal/templates/portal/_sidebar.html` (dynamic name, logout), all portal templates, `static/portal/js/api.js` (replaces services/*), `dashboard.js` (replaces transfer.js), `send_money.js`, `transactions.js`, `accounts.js`, `fraud_shield.js`.
Check: browser run — login, send low-risk, send held → OTP (console) → verify, cancel, history.

## Task 10 — SOC rewire
Files: `soc/{services,views,urls,models,admin}.py`, `soc/migrations/0002_*.py`, templates; delete `alert_rules.html`, `model_insights.html`, `settings.html`; `soc/tests.py`.
Check: tests (staff required; release calls the API + writes AuditLog; CSV export) + browser run.

## Task 11 — n8n workflow, run script, README
Files: `backend/n8n/The-Safest-Bank.json`, `run.py`, `README.md`.
Check: `python run.py test` is green; fresh clone → `python run.py` works.
