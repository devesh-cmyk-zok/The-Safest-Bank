"""
FILE: app/main.py
PURPOSE:
    Primary application entrypoint for 'The Safest Bank' API.
    Exposes health telemetry, transactional escrow routing endpoints,
    LangGraph agent orchestration, and n8n webhook notification dispatchers.
"""

import uuid
import os
import httpx
from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text, func

import database.models as models
from database.connection import engine, Base, get_db
from database.models import User, Transaction, EscrowStatus
from app.schemas import TransferRequest, TransferResponse, EscrowActionRequest, EscrowActionResponse
from app.engine import risk_engine
from app.webhook import dispatch_quarantine_event
from app.langgraph_agents import fraud_agent_app
from services.otp_service import generate_and_store_otp, verify_otp
from services.n8n_dispatcher import trigger_n8n_workflow

# Initialize DB Tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="The Safest Bank - Autonomous Fraud Engine")

# CORS Configuration
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Open for development/demo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Schemas ---

class EvaluateTransactionRequest(BaseModel):
    transaction_id: str
    user_id: str
    amount: float
    distance_km: float = 0.0
    is_new_device: bool = False
    velocity_1h: int = 1
    otp_verified: bool = False

class VerifyOTPRequest(BaseModel):
    transaction_id: str
    otp: str

# --- Health Check Endpoints ---

@app.get("/")
async def root():
    return {
        "system": "The Safest Bank",
        "status": "online",
        "phase": "Phase 4 n8n Dispatcher Active",
        "agents_active": ["ThreatAnalyst", "EscrowExecutor", "SOCAnalyst", "UserConcierge"]
    }

@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"disconnected: {str(e)}"
        
    return {
        "api_status": "healthy",
        "database": db_status
    }

@app.get("/api/v1/graph-image")
def get_graph_image():
    """Generates visual diagram of the 4-agent LangGraph workflow."""
    image_bytes = fraud_agent_app.get_graph().draw_mermaid_png()
    return Response(content=image_bytes, media_type="image/png")

# --- Agentic Evaluation Endpoint ---

@app.post("/api/v1/transactions/evaluate")
async def evaluate_transaction(payload: EvaluateTransactionRequest, background_tasks: BackgroundTasks):
    """
    Evaluates transaction telemetry using 4-Agent LangGraph Pipeline.
    Triggers n8n background notifications for escrow or auto-abort events.
    """
    initial_state = payload.dict()
    agent_output = fraud_agent_app.invoke(initial_state)

    decision = agent_output["decision"]
    risk_score = agent_output["risk_score"]
    otp_code = None

    if decision == "ESCROW_HELD":
        otp_code = generate_and_store_otp(payload.transaction_id)

    # Execution trace payload for UI visualization
    agent_execution_trace = [
        {
            "agent": "Threat Analyst Agent",
            "status": "COMPLETED",
            "output": f"Risk Score: {risk_score} | SHAP Breakdown: {agent_output['xai_breakdown']}"
        },
        {
            "agent": "Escrow Executor Agent",
            "status": "COMPLETED",
            "output": f"Decision: {decision} | Reason: {agent_output['action_reason']}"
        },
        {
            "agent": "SOC Analyst Agent",
            "status": "COMPLETED",
            "output": f"Severity: {agent_output['soc_report']['severity']} | Incident ID: {agent_output['soc_report']['incident_id']}"
        },
        {
            "agent": "User Concierge Agent",
            "status": "COMPLETED",
            "output": agent_output["user_message"]
        }
    ]

    # Trigger n8n webhook workflow asynchronously on quarantine or block
    if decision in ["ESCROW_HELD", "AUTO_ABORT"]:
        webhook_payload = {
            "transaction_id": payload.transaction_id,
            "user_id": payload.user_id,
            "decision": decision,
            "risk_score": risk_score,
            "user_message": agent_output["user_message"],
            "soc_report": agent_output["soc_report"],
            "otp_code": otp_code
        }
        background_tasks.add_task(trigger_n8n_workflow, webhook_payload)

    return {
        "transaction_id": payload.transaction_id,
        "risk_score": risk_score,
        "decision": decision,
        "action_reason": agent_output["action_reason"],
        "xai_breakdown": agent_output["xai_breakdown"],
        "soc_report": agent_output["soc_report"],
        "user_message": agent_output["user_message"],
        "agent_execution_trace": agent_execution_trace,
        "dev_debug_otp": otp_code
    }

# --- OTP Verification ---

@app.post("/api/v1/transactions/verify-otp")
def verify_transaction_otp(payload: VerifyOTPRequest):
    is_valid = verify_otp(payload.transaction_id, payload.otp)
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    
    return {
        "transaction_id": payload.transaction_id,
        "status": "VERIFIED",
        "action": "RELEASE_ESCROW",
        "message": "Step-up authentication successful. Escrow funds released."
    }

# --- Database & Ledger Transfer Endpoints ---

@app.post("/api/v1/transfer", response_model=TransferResponse)
async def initiate_transfer(payload: TransferRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Sender account '{payload.user_id}' not found.")

    if user.account_balance < payload.amount:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Insufficient funds. Balance: ₹{user.account_balance}")

    risk_score, escrow_status, xai_breakdown = risk_engine.evaluate_transaction(
        amount=payload.amount,
        delta_t_ms=payload.delta_t_ms,
        ip_distance_km=payload.ip_distance_km,
        device_hash=payload.device_hash
    )

    tx_id = f"tx_{uuid.uuid4().hex[:10]}"
    requires_soc = (escrow_status == EscrowStatus.ESCROW_HELD)
    hold_period = 300 if escrow_status == EscrowStatus.ESCROW_HELD else 0

    transaction = models.Transaction(
        id=tx_id,
        user_id=user.id,
        amount=payload.amount,
        recipient_id=payload.recipient_id,
        delta_t_ms=payload.delta_t_ms,
        ip_distance_km=payload.ip_distance_km,
        device_hash=payload.device_hash,
        risk_score=risk_score,
        status=escrow_status,
        xai_breakdown=xai_breakdown
    )

    if escrow_status == EscrowStatus.SETTLED:
        user.account_balance -= payload.amount
        message = "Transfer settled instantly. No behavioral risk detected."
    else:
        message = f"High-risk telemetry detected (Risk: {risk_score}). Transaction detained in Escrow Quarantine."

    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    if escrow_status == EscrowStatus.ESCROW_HELD:
        background_tasks.add_task(
            dispatch_quarantine_event,
            transaction_id=tx_id,
            user_id=user.id,
            recipient_id=payload.recipient_id,
            amount=payload.amount,
            risk_score=risk_score,
            xai_breakdown=xai_breakdown
        )

    return TransferResponse(
        transaction_id=tx_id,
        status=escrow_status,
        risk_score=risk_score,
        message=message,
        requires_soc_review=requires_soc,
        hold_period_seconds=hold_period,
        xai_breakdown=xai_breakdown
    )

@app.post("/api/v1/escrow/release", response_model=EscrowActionResponse)
def release_escrow(payload: EscrowActionRequest, db: Session = Depends(get_db)):
    tx = db.query(models.Transaction).filter(models.Transaction.id == payload.transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if tx.status != models.EscrowStatus.ESCROW_HELD:
        raise HTTPException(status_code=400, detail=f"Cannot release transaction with status '{tx.status.value}'. Must be in 'ESCROW_HELD'.")

    recipient = db.query(models.User).filter(models.User.id == tx.recipient_id).first()
    if recipient:
        recipient.account_balance += tx.amount

    prev_status = tx.status.value
    tx.status = models.EscrowStatus.SETTLED
    db.commit()

    return EscrowActionResponse(
        transaction_id=tx.id,
        previous_status=prev_status,
        new_status=tx.status.value,
        message="Transaction successfully cleared by SOC. Funds settled to recipient.",
        resolution_notes=payload.reason
    )

@app.post("/api/v1/escrow/refund", response_model=EscrowActionResponse)
def refund_escrow(payload: EscrowActionRequest, db: Session = Depends(get_db)):
    tx = db.query(models.Transaction).filter(models.Transaction.id == payload.transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if tx.status != models.EscrowStatus.ESCROW_HELD:
        raise HTTPException(status_code=400, detail=f"Cannot refund transaction with status '{tx.status.value}'. Must be in 'ESCROW_HELD'.")

    sender = db.query(models.User).filter(models.User.id == tx.user_id).first()
    if sender:
        sender.account_balance += tx.amount

    prev_status = tx.status.value
    tx.status = models.EscrowStatus.AUTO_ABORTED
    db.commit()

    return EscrowActionResponse(
        transaction_id=tx.id,
        previous_status=prev_status,
        new_status=tx.status.value,
        message="Fraud confirmed. Funds refunded to sender account.",
        resolution_notes=payload.reason
    )

@app.get("/api/v1/escrow/quarantined")
def list_quarantined_transactions(db: Session = Depends(get_db)):
    return db.query(models.Transaction).filter(
        models.Transaction.status == models.EscrowStatus.ESCROW_HELD
    ).order_by(models.Transaction.timestamp.desc()).all()

@app.get("/api/v1/users/{user_id}")
def get_user_profile(user_id: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "user_id": user.id,
        "full_name": user.full_name,
        "account_balance": user.account_balance,
        "created_at": user.created_at
    }

@app.get("/api/v1/transactions/{user_id}")
def get_user_transactions(user_id: str, db: Session = Depends(get_db)):
    return db.query(models.Transaction).filter(
        (models.Transaction.user_id == user_id) | (models.Transaction.recipient_id == user_id)
    ).order_by(models.Transaction.timestamp.desc()).all()

@app.get("/api/v1/admin/stats", tags=["SOC Admin"])
def get_soc_dashboard_stats(db: Session = Depends(get_db)):
    total_tx_count = db.query(models.Transaction).count()

    quarantined_txs = db.query(models.Transaction).filter(models.Transaction.status == models.EscrowStatus.ESCROW_HELD).all()
    quarantined_count = len(quarantined_txs)
    quarantined_volume = sum(tx.amount for tx in quarantined_txs)

    aborted_txs = db.query(models.Transaction).filter(models.Transaction.status == models.EscrowStatus.AUTO_ABORTED).all()
    prevented_count = len(aborted_txs)
    fraud_prevented_volume = sum(tx.amount for tx in aborted_txs)

    settled_txs = db.query(models.Transaction).filter(models.Transaction.status == models.EscrowStatus.SETTLED).all()
    settled_count = len(settled_txs)
    settled_volume = sum(tx.amount for tx in settled_txs)

    avg_risk = db.query(func.avg(models.Transaction.risk_score)).scalar() or 0.0

    return {
        "total_transactions": total_tx_count,
        "settled": {"count": settled_count, "volume": round(settled_volume, 2)},
        "escrow_quarantined": {"count": quarantined_count, "volume": round(quarantined_volume, 2)},
        "fraud_prevented": {"count": prevented_count, "volume": round(fraud_prevented_volume, 2)},
        "average_risk_score": round(float(avg_risk), 3)
    }

@app.get("/api/v1/admin/users/{user_id}/investigate", tags=["SOC Admin"])
def investigate_user_360(user_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    transactions = db.query(Transaction).filter(
        (Transaction.user_id == user_id) | (Transaction.recipient_id == user_id)
    ).order_by(Transaction.timestamp.desc()).all()

    active_quarantines = [tx for tx in transactions if tx.status == EscrowStatus.ESCROW_HELD]
    total_flagged = len([tx for tx in transactions if tx.risk_score >= 0.60])

    return {
        "user_profile": {
            "user_id": user.id,
            "name": getattr(user, "full_name", "User Account"),
            "current_balance": user.account_balance,
            "account_status": "FLAGGED_MONITORING" if active_quarantines else "HEALTHY",
        },
        "security_summary": {
            "total_transactions_analyzed": len(transactions),
            "total_high_risk_flagged": total_flagged,
            "active_escrow_holds": len(active_quarantines)
        },
        "active_quarantined_transfers": [
            {
                "transaction_id": tx.id,
                "amount": tx.amount,
                "recipient_id": tx.recipient_id,
                "risk_score": tx.risk_score,
                "xai_breakdown": tx.xai_breakdown
            } for tx in active_quarantines
        ]
    }