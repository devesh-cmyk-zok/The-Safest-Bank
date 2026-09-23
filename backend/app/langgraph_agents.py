from typing import TypedDict, Dict, Any
from langgraph.graph import StateGraph, END
from services.shap_engine import calculate_shap_attributions

# Define Graph State Schema
class FraudAgentState(TypedDict):
    transaction_id: str
    user_id: str
    amount: float
    distance_km: float
    is_new_device: bool
    velocity_1h: int
    otp_verified: bool
    risk_score: float
    xai_breakdown: Dict[str, Any]
    decision: str
    action_reason: str
    soc_report: Dict[str, Any]
    user_message: str

# 1. THREAT ANALYST AGENT
def threat_analyst_agent(state: FraudAgentState) -> Dict[str, Any]:
    shap_results = calculate_shap_attributions({
        "amount": state.get("amount", 0.0),
        "distance_km": state.get("distance_km", 0.0),
        "is_new_device": state.get("is_new_device", False),
        "velocity_1h": state.get("velocity_1h", 1)
    })
    return {
        "risk_score": shap_results["composite_risk"],
        "xai_breakdown": shap_results["signal_attribution"]
    }

# 2. ESCROW EXECUTOR AGENT
def escrow_executor_agent(state: FraudAgentState) -> Dict[str, Any]:
    risk_score = state.get("risk_score", 0.0)
    otp_verified = state.get("otp_verified", False)

    if risk_score >= 0.85 and not otp_verified:
        decision = "AUTO_ABORT"
        reason = "Critical risk score detected (>0.85). Transaction blocked automatically."
    elif risk_score > 0.60 and not otp_verified:
        decision = "ESCROW_HELD"
        reason = "High risk score detected (>0.60). Funds locked in escrow pending step-up OTP."
    else:
        decision = "SETTLE"
        reason = "Low risk or step-up authentication verified. Transaction released."

    return {"decision": decision, "action_reason": reason}

# 3. SOC ANALYST AGENT (For Security Team Incident Reports)
def soc_analyst_agent(state: FraudAgentState) -> Dict[str, Any]:
    risk = state.get("risk_score", 0.0)
    decision = state.get("decision", "SETTLE")
    xai = state.get("xai_breakdown", {})
    
    severity = "CRITICAL" if risk >= 0.85 else ("HIGH" if risk > 0.60 else "LOW")
    
    report = {
        "incident_id": f"INC-{state.get('transaction_id')}",
        "severity": severity,
        "action_taken": decision,
        "primary_threat_drivers": [k for k, v in xai.items() if v > 0.3],
        "recommended_action": "Freeze user account & mandate KYC verification" if severity == "CRITICAL" else "Monitor next 24h transactions"
    }
    return {"soc_report": report}

# 4. USER CONCIERGE AGENT (Plain-English Explanations for End Users)
def user_concierge_agent(state: FraudAgentState) -> Dict[str, Any]:
    decision = state.get("decision", "SETTLE")
    amount = state.get("amount", 0.0)
    
    if decision == "ESCROW_HELD":
        msg = f"We noticed unusual activity on your recent ${amount:,.2f} payment. To keep your account safe, we've temporarily paused this transaction. Please verify the 6-digit code sent to your device to authorize it."
    elif decision == "AUTO_ABORT":
        msg = f"Your transaction of ${amount:,.2f} was declined due to severe security flags. If you believe this is an error, please contact support immediately."
    else:
        msg = f"Your transaction of ${amount:,.2f} was successfully processed and settled."

    return {"user_message": msg}

# BUILD GRAPH
workflow = StateGraph(FraudAgentState)

workflow.add_node("threat_analyst", threat_analyst_agent)
workflow.add_node("escrow_executor", escrow_executor_agent)
workflow.add_node("soc_analyst", soc_analyst_agent)
workflow.add_node("user_concierge", user_concierge_agent)

workflow.set_entry_point("threat_analyst")
workflow.add_edge("threat_analyst", "escrow_executor")
workflow.add_edge("escrow_executor", "soc_analyst")
workflow.add_edge("soc_analyst", "user_concierge")
workflow.add_edge("user_concierge", END)

fraud_agent_app = workflow.compile()