# The Safest Bank — Setup & Demo Guide

Short version. The full write-up (architecture, scoring, security, limits) is in `README.md`.

## What it is

A demo bank where every transfer is screened for fraud **before any money moves**.
Risky transfers are held until the customer enters a code emailed via n8n; very risky
ones are declined. Analysts handle held transfers in a Security Operations Center (SOC).

| Part | Tech | Port |
|---|---|---|
| Customer portal + SOC | Django | 8000 |
| Fraud engine (signals, PyTorch model + rules, LangGraph, ledger, OTP) | FastAPI | 8001 |
| OTP email + SOC alerts | n8n (optional) | 5678 |

## 1. Install (any Windows / macOS / Linux machine)

Needs **Python 3.11 or newer** (https://www.python.org/downloads/, tick "Add to PATH" on Windows).

Unzip, open a terminal in the `The-Safest-Bank` folder, then:

**Windows**
```bat
python -m venv .venv
.venv\Scripts\activate
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
python run.py
```

**macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
python run.py
```

The first run creates `.env` with fresh random keys, sets up the databases, seeds the
demo data and starts both servers. Open **http://127.0.0.1:8000**. Stop with `Ctrl+C`.

Next time just activate the venv and run `python run.py`.

| Command | What it does |
|---|---|
| `python run.py` | start everything |
| `python run.py test` | run all tests (60) |
| `python run.py seed --reset` | wipe and reseed the demo data |

## 2. Log in

Password for every account: **demo123**

| Username | Role |
|---|---|
| `aarav`, `priya` | customers (the first browser you use becomes their trusted device) |
| `rohan`, `ananya`, `vikram` | customers with pre-seeded fraud scenarios |
| `analyst` | SOC analyst, lands on `/soc/` |

## 3. Demo script

Sign in as **aarav** → **Send money**:

1. **Normal payment**: pay Priya **₹2,000** → *Completed*, risk ≈ 3/100.
2. **Held for verification**: tick **New device**, pay Vikram **₹10,000** → *On hold*, risk ≈ 82/100.
   The code arrives by email through n8n, or, without n8n, it is printed in the terminal
   running `run.py` (line starting `[DEMO] ... OTP for tx_...`). Click **Enter code**, type it
   → *Completed*. Or click **Cancel transfer** → money returns instantly.
3. **Account takeover**: tick **New device** and **1,800 km away**, pay QuickCash Services
   **₹10,000** → *Declined*, risk ≈ 88/100. Nothing moves; the SOC is alerted.
4. Sign out, sign in as **analyst**: **Held Transfers** shows seeded cases (Ananya ₹30,000,
   Rohan's bot burst). **Investigate & act** → **Release** or **Block & refund** → check **Audit Log**.
   Also look at **Risk Analytics** and **Model Health**.

If repeated tries start getting *declined* instead of *held*, that's the velocity signal
(many transfers in one hour). Run `python run.py seed --reset` for a clean slate.

## 4. n8n (optional: real OTP emails)

Nothing in the code needs to change. Import the workflow that ships with the project:

1. In n8n: **Workflows → Import from file →** `backend/n8n/The-Safest-Bank.json`.
   If you imported an older version before, replace it: the old one emailed a fixed
   address and posted the OTP to Discord.
2. Open node **Email OTP to customer** → choose your **Gmail** credential.
3. Open node **Alert SOC on Discord** → paste your Discord webhook URL
   (it replaces `REPLACE_WITH_YOUR_WEBHOOK`; this node never receives the OTP).
4. **Activate** the workflow and copy the Webhook node's **Production URL**.
5. Edit `.env` in the project folder:
   ```
   N8N_WEBHOOK_URL=http://localhost:5678/webhook/fraud-alert
   DEMO_OTP_EMAIL=you@gmail.com
   ```
   `DEMO_OTP_EMAIL` gives the demo customers plus-addresses (`you+aarav@gmail.com`, …)
   so every OTP lands in your inbox.
6. Run `python run.py seed --reset` (applies the new emails), then `python run.py`.
7. Optional hardening: set `N8N_WEBHOOK_SECRET=some-long-random-string` in `.env` and turn
   on **Header Auth** in the Webhook node with header `X-Webhook-Secret` and the same value.

The engine must be able to reach n8n: local n8n works for a local run; a hosted app
needs n8n Cloud or a publicly reachable n8n URL.

## 5. Settings (`.env`)

Created automatically from `.env.example` on first run.

| Variable | Meaning |
|---|---|
| `SERVICE_API_KEY` | shared secret between Django and the engine (auto-generated) |
| `DJANGO_SECRET_KEY` | Django signing key (auto-generated) |
| `DEBUG` | `true` for local use |
| `DEMO_MODE` | `true` shows the *Simulate* panel and prints OTPs to the console when n8n isn't set |
| `DATABASE_URL` | leave unset for local SQLite; a Postgres URL also works (then `python backend/seed.py --reset`) |
| `N8N_WEBHOOK_URL`, `N8N_WEBHOOK_SECRET`, `DEMO_OTP_EMAIL` | n8n delivery, see above |

## 6. Hosting

Runs anywhere that keeps two Python processes running (Render, Railway, a VPS).
It does **not** fit Vercel as-is: PyTorch exceeds Vercel's function size limit, there is
no persistent disk for the databases, and Vercel runs single short-lived functions.

## 7. Troubleshooting

| Problem | Fix |
|---|---|
| `python` not found | install Python 3.11+ and reopen the terminal (Windows: tick "Add to PATH") |
| Port 8000/8001 in use | close the other app using it, or stop an old `run.py` |
| "The fraud engine is unreachable" | the engine didn't start; read the terminal output of `run.py` |
| OTP never arrives | without n8n it is printed in the terminal; with n8n check the workflow is **active** and `N8N_WEBHOOK_URL` is the **Production** URL |
| Everything gets declined | velocity from many tries: `python run.py seed --reset` |
