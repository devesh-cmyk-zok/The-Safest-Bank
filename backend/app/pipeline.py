"""The decision pipeline as a LangGraph state graph: four deterministic stages, no LLM calls.

threat_analyst -> escrow_executor -> soc_analyst -> user_concierge
"""

from typing import TypedDict

from langgraph.graph import END, StateGraph

from app import engine
from database.models import TxStatus


class State(TypedDict, total=False):
    risks: dict
    amount_paise: int
    risk_score: float
    nn_score: float
    rule_score: float
    contributions: dict
    reasons: list
    status: TxStatus
    soc_report: dict
    user_message: str


def inr(paise: int) -> str:
    """₹ with Indian digit grouping: 1,23,456.78"""
    rupees, p = divmod(int(paise), 100)
    s = str(rupees)
    head, tail = s[:-3], s[-3:]
    while len(head) > 2:
        tail = f"{head[-2:]},{tail}"
        head = head[:-2]
    return f"₹{head + ',' if head else ''}{tail}.{p:02d}"


def threat_analyst(state: State) -> State:
    risks = state["risks"]
    return {**engine.score(risks), "contributions": engine.contributions(risks), "reasons": engine.reasons(risks)}


def escrow_executor(state: State) -> State:
    return {"status": engine.decide(state["risk_score"])}


def soc_analyst(state: State) -> State:
    score = state["risk_score"]
    severity = "CRITICAL" if score >= engine.ABORT_AT else "HIGH" if score >= engine.HOLD_AT else \
        "MEDIUM" if score >= 0.3 else "LOW"
    action = {
        TxStatus.AUTO_ABORTED: "Declined automatically. Contact the customer and review the account.",
        TxStatus.ESCROW_HELD: "Held pending customer OTP. Release or refund if it stays held.",
    }.get(state["status"], "No action needed.")
    return {"soc_report": {"severity": severity, "drivers": state["reasons"], "recommended_action": action}}


def user_concierge(state: State) -> State:
    amount = inr(state["amount_paise"])
    status = state["status"]
    if status == TxStatus.ESCROW_HELD:
        msg = (f"Your transfer of {amount} looks unusual, so we're holding it safely. "
               "Enter the code we emailed you to release it, or cancel to get your money back.")
    elif status == TxStatus.AUTO_ABORTED:
        msg = f"We declined your transfer of {amount} because it matches known fraud patterns. No money has left your account."
    else:
        msg = f"Your transfer of {amount} was sent."
    return {"user_message": msg}


_graph = StateGraph(State)
for _name, _fn in [("threat_analyst", threat_analyst), ("escrow_executor", escrow_executor),
                   ("soc_analyst", soc_analyst), ("user_concierge", user_concierge)]:
    _graph.add_node(_name, _fn)
_graph.set_entry_point("threat_analyst")
_graph.add_edge("threat_analyst", "escrow_executor")
_graph.add_edge("escrow_executor", "soc_analyst")
_graph.add_edge("soc_analyst", "user_concierge")
_graph.add_edge("user_concierge", END)
graph = _graph.compile()


def run(risks: dict, amount_paise: int) -> dict:
    return graph.invoke({"risks": risks, "amount_paise": amount_paise})
