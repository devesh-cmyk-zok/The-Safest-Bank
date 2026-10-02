"""
FILE: app/schemas.py
PURPOSE:
    Defines Pydantic data validation schemas for API requests and responses.
    Captures financial transaction payloads alongside behavioral telemetry
    (typing cadence, IP geodistance, and hardware fingerprints) to feed the
    real-time risk scoring engine.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from database.models import EscrowStatus

class TransferRequest(BaseModel):
    user_id: str = Field(..., example="usr_1001", description="Unique sender ID")
    recipient_id: str = Field(..., example="usr_2002", description="Target beneficiary ID")
    amount: float = Field(..., gt=0, example=25000.0, description="Transfer amount in currency units")
    
    recipient_name: Optional[str] = Field(None, description="Display name for the beneficiary")

    # Behavioral & Network Telemetry
    delta_t_ms: int = Field(
        145,
        example=145,
        description="Average keypress/input interval in milliseconds (distinguishes bots/scripts from humans)"
    )
    ip_distance_km: float = Field(
        12.0,
        example=850.5,
        description="Geographical distance in KM from user's primary historical location"
    )
    device_hash: str = Field(
        "a9f4c3d2e1b0",
        example="a9f4c3d2e1b0...",
        description="Browser/device fingerprint hash (screens, canvas, platform)"
    )

class TransferResponse(BaseModel):
    transaction_id: str
    status: EscrowStatus
    risk_score: float
    message: str
    requires_soc_review: bool
    hold_period_seconds: int
    xai_breakdown: Optional[Dict[str, Any]] = None
    user_message: Optional[str] = None
    reasons: Optional[list] = None
    decision: Optional[str] = None
    fraud_probability: Optional[float] = None
    fraud_reason: Optional[str] = None
    dev_debug_otp: Optional[str] = None

    class Config:
        from_attributes = True

from typing import Optional

class EscrowActionRequest(BaseModel):
    transaction_id: str
    admin_or_agent_id: str
    reason: str

class EscrowActionResponse(BaseModel):
    transaction_id: str
    previous_status: str
    new_status: str
    message: str
    resolution_notes: str