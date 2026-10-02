# The Safest Bank — Showcase Overhaul Design

Date: 2026-09-23 · Branch: `showcase-overhaul` · Baseline: `c840f3f`

## Goal

Turn the project into an honest, working portfolio showcase: every number on screen comes
from real data, the step-up auth can't be bypassed, and it runs locally with one command.
Out of scope: Docker, JWT, Alembic, CI, deployment.

## 1. Architecture: Django is the only thing the browser talks to

```
Browser ──session+CSRF──▶ Django (portal + SOC, :8000)
                              │  X-Service-Key + acting user id
                              ▼
                          FastAPI engine (:8001) ──▶ SQLite/Postgres
                              │ background POST (+ optional X-Webhook-Secret)
                              ▼
                          n8n webhook ──▶ Gmail (OTP to account holder) / Discord (SOC alert)
```

- FastAPI requires `X-Service-Key == SERVICE_API_KEY` on every `/api/*` route (401 otherwise).
  CORS middleware removed. `/health` stays public.
- Django gateway views (`/api/...` on Django) take the user id from the session, never the request body.
  Customer routes: me, my transactions, transfer, verify-otp, cancel-held.
  SOC routes (staff only): release, refund, block, plus reads.
- Portal JS calls same-origin Django URLs and sends the CSRF token.

## 2. OTP via n8n

- A held transfer creates the OTP, then a background POST goes to `N8N_WEBHOOK_URL` with
  `{event, decision:"ESCROW_HELD", transaction_id, user_id, email, full_name, amount, risk_score, reasons, user_message, otp_code}`.
- The OTP never appears in any API response. The `123456` fallback is deleted.
- OTP: 6 digits from `secrets`, 5-minute TTL, max 5 attempts. After 5 wrong tries the OTP is dead
  and the transfer stays held for SOC. Stored hashed (Redis if reachable, else in memory).
- No `N8N_WEBHOOK_URL` and `DEMO_MODE=true`: the OTP is logged to the FastAPI console.
- `User.email` added and seeded.
- Workflow JSON: Gmail `sendTo = {{ $json.body.email }}`. The Discord branch becomes a SOC alert with no OTP,
  for both HELD and AUTO_ABORT. The webhook URL is a placeholder. Header Auth documented.
- The public `webhook.site` default is removed (`app/webhook.py` deleted; one dispatcher remains).

## 3. Fraud engine

Single scoring path `score_transfer(db, user, payload) -> Assessment`, used by `/transfer`.
The LangGraph graph wraps it (threat → escrow decision → SOC report → customer message),
so the "4 agents" are the real pipeline, not a parallel formula. Messages use ₹.

Features. Server-side ones are computed from the DB; the client is never trusted for them.

| feature | source |
|---|---|
| amount_ratio = amount / user's median past outgoing (floor ₹1,000) | DB |
| velocity_1h = user's outgoing count in the last hour | DB |
| new_payee = never sent to this recipient before | DB |
| new_device = device_id not in the user's `KnownDevice` rows | DB + client device id |
| cadence_ms = median keystroke interval on the transfer form (null if pasted/none) | browser |
| distance_km = optional, only via the demo Simulate panel (no GeoIP) | simulated |

- Rules produce per-signal risks in [0,1]. The MLP (same 5→16→8→1 shape, input = 6 features)
  produces nn_score. Composite = 0.6·nn + 0.4·rules.
- Thresholds: ≥ 0.85 AUTO_ABORT (refund sender immediately), ≥ 0.60 ESCROW_HELD, else SETTLED.
- Explanations are per-signal contributions (rule weight × risk), labelled honestly as
  "signal contributions", not SHAP.
- A successful OTP release or settle marks the device as known.
- `backend/train_model.py`: seeded synthetic generator (legit profiles plus fraud patterns: bot cadence,
  new device + new payee + large amount, velocity burst, far location), stratified split,
  trains the MLP, writes `fraud_model.pth` + `model_metrics.json` (accuracy, precision, recall, F1,
  ROC-AUC on the held-out set, permutation feature importance, dataset size, trained_at).
  Metrics describe synthetic data and are labelled so.
- Demo "Simulate" panel on Send Money (only when `DEMO_MODE=true`): new device / far location / bot typing.
  Overrides are sent as `simulate:{...}` and stored on the transaction as `simulated=true`.

Money: `Numeric(14,2)` / `Decimal`. Timestamps are timezone-aware UTC.

## 4. SOC (Django)

- Delete the demo fixtures in `soc/services.py`. Data comes from FastAPI admin endpoints via the gateway client.
- Delete the Django `FraudTransaction`, `ShapFeature`, `BankAccount`, `ModelMetrics` and `AlertRule` models
  (they duplicate FastAPI data or do nothing). Keep `SecurityCase` and `AuditLog`.
- Pages: Dashboard (real KPIs + held queue), Transactions (filter/search), Alerts (held + aborted),
  Verification (held queue with release/refund), Users & Accounts, Analytics (computed from real transactions),
  Cases, Audit Logs, Model Health (from `model_metrics.json`, which now includes the Model Insights content),
  Reports (real CSV exports: transactions, audit trail; the PDF buttons are removed).
- Delete Alert Rules, Model Insights and Settings (the Settings form saved nothing).
- Every analyst action is written to AuditLog. Releasing, refunding or blocking really moves money in FastAPI.

## 5. Customer portal

- History, balance and profile come from the API only. The localStorage ledger and default fake rows are deleted.
- All user-provided strings are rendered via `textContent` or escaped. No `innerHTML` with data.
- Recipients: a real payee picker from seeded users (`GET /api/payees`) or a typed `usr_` id.
  The name-sniffing `resolve_recipient_id` is deleted.
- Demo users: the `seed_demo` management command creates Django users with hashed passwords linked to FastAPI
  user ids (`PortalProfile` model). The password dict in code is deleted.

## 6. Hygiene

- One `requirements.txt` at the root (UTF-8). `.env.example`. `SECRET_KEY`, `DEBUG` and `ALLOWED_HOSTS` come from env.
- `frontend/staticfiles/` and `db.sqlite3` are untracked. WhiteNoise stays for static files.
- `run.py` (or `scripts/dev.ps1` + `.sh`): seed if needed, start both servers.
- Tests (pytest):
  - backend: engine thresholds, OTP attempts and expiry, transfer ledger invariants (money conserved),
    auth rejection without the service key, no OTP in responses, AUTO_ABORT refunds.
  - Django: the gateway uses the session user and ignores a body `user_id`, SOC requires staff, CSRF enforced.
- README: what it is, architecture diagram, a real "how the score is computed" section, demo script, honest limits.
