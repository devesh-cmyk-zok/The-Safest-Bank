import enum
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, Enum, ForeignKey, Integer, JSON
from sqlalchemy.orm import relationship
from .connection import Base

class EscrowStatus(str, enum.Enum):
    PENDING = "PENDING"
    ESCROW_HELD = "ESCROW_HELD"
    SETTLED = "SETTLED"
    AUTO_ABORTED = "AUTO_ABORTED"
    BLOCKED_BY_SOC = "BLOCKED_BY_SOC"

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    account_balance = Column(Float, default=100000.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    transactions = relationship("Transaction", back_populates="user")

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))
    amount = Column(Float, nullable=False)
    recipient_id = Column(String, nullable=False)
    
    # Behavioral & Device Telemetry
    delta_t_ms = Column(Integer)
    ip_distance_km = Column(Float)
    device_hash = Column(String)
    
    # Risk Engine Output
    risk_score = Column(Float)
    status = Column(Enum(EscrowStatus), default=EscrowStatus.PENDING)
    xai_breakdown = Column(JSON, nullable=True)
    
    timestamp = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="transactions")