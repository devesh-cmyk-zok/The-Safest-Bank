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
    
    # Behavioral & Network Telemetry
    delta_t_ms: int = Field(
        ..., 
        example=145, 
        description="Average keypress/input interval in milliseconds (distinguishes bots/scripts from humans)"
    )
    ip_distance_km: float = Field(
        ..., 
        example=850.5, 
        description="Geographical distance in KM from user's primary historical location"
    )
    device_hash: str = Field(
        ..., 
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