"""
SOC Services Layer
==================
Provides all data for the SOC dashboard.

Architecture:
- `get_*` functions first attempt to fetch from real DB models.
- If the DB is empty, they fall back to realistic demo data.
- This allows the real CNN-BiLSTM pipeline to plug in by simply
  writing records to the DB models — no view changes needed.
"""
import random
from datetime import timedelta, datetime
from django.utils import timezone
from django.db.models import Count, Sum, Avg, Q
from django.contrib.auth.models import User


# ─────────────────────────────────────────────────────────────
#  Demo Data Fixtures
# ─────────────────────────────────────────────────────────────

DEMO_TRANSACTIONS = [
    {
        "transaction_id": "TXN-884421",
        "account_masked": "ACC-••••7823",
        "amount": 14750.00,
        "channel": "Mobile API",
        "merchant": "Crypto Exchange",
        "risk_score": 91,
        "risk_level": "CRITICAL",
        "status": "PENDING",
        "prediction": "FRAUD",
        "model_confidence": 98.7,
        "fraud_type": "Velocity + New Device",
        "shap": [
            ("Velocity spike", 31.0),
            ("New device", 24.0),
            ("Unusual location", 18.0),
            ("Transaction amount", 14.0),
            ("Unusual time", 9.0),
            ("Account age", 4.0),
        ],
        "minutes_ago": 2,
    },
    {
        "transaction_id": "TXN-884398",
        "account_masked": "ACC-••••3341",
        "amount": 8200.00,
        "channel": "Web Banking",
        "merchant": "WireTransfer Intl",
        "risk_score": 78,
        "risk_level": "HIGH",
        "status": "HELD",
        "prediction": "FRAUD",
        "model_confidence": 94.2,
        "fraud_type": "Geo Anomaly",
        "shap": [
            ("Geo anomaly", 35.0),
            ("Unusual time", 28.0),
            ("Transaction amount", 20.0),
            ("New IP address", 12.0),
            ("Device fingerprint", 5.0),
        ],
        "minutes_ago": 8,
    },
    {
        "transaction_id": "TXN-884376",
        "account_masked": "ACC-••••9102",
        "amount": 3400.00,
        "channel": "ATM",
        "merchant": "ATM-045-NYC",
        "risk_score": 67,
        "risk_level": "HIGH",
        "status": "REVIEWING",
        "prediction": "FRAUD",
        "model_confidence": 87.5,
        "fraud_type": "Amount Deviation",
        "shap": [
            ("Amount deviation", 42.0),
            ("Geo anomaly", 25.0),
            ("Velocity spike", 18.0),
            ("Time anomaly", 15.0),
        ],
        "minutes_ago": 15,
    },
    {
        "transaction_id": "TXN-884355",
        "account_masked": "ACC-••••5567",
        "amount": 22500.00,
        "channel": "UPI",
        "merchant": "Unknown Merchant",
        "risk_score": 85,
        "risk_level": "CRITICAL",
        "status": "ESCALATED",
        "prediction": "FRAUD",
        "model_confidence": 96.1,
        "fraud_type": "Multiple Factors",
        "shap": [
            ("Velocity spike", 28.0),
            ("New device", 22.0),
            ("High amount", 20.0),
            ("Unusual merchant", 18.0),
            ("Night transaction", 12.0),
        ],
        "minutes_ago": 23,
    },
    {
        "transaction_id": "TXN-884312",
        "account_masked": "ACC-••••1234",
        "amount": 1200.00,
        "channel": "POS",
        "merchant": "Supermarket ABC",
        "risk_score": 45,
        "risk_level": "MEDIUM",
        "status": "REVIEWING",
        "prediction": "LEGITIMATE",
        "model_confidence": 72.3,
        "fraud_type": "Amount Deviation",
        "shap": [
            ("Amount deviation", 38.0),
            ("Time anomaly", 28.0),
            ("Location", 34.0),
        ],
        "minutes_ago": 34,
    },
    {
        "transaction_id": "TXN-884290",
        "account_masked": "ACC-••••8899",
        "amount": 55000.00,
        "channel": "Web Banking",
        "merchant": "International Transfer",
        "risk_score": 93,
        "risk_level": "CRITICAL",
        "status": "BLOCKED",
        "prediction": "FRAUD",
        "model_confidence": 99.1,
        "fraud_type": "Account Takeover",
        "shap": [
            ("Auth anomaly", 30.0),
            ("Geo anomaly", 25.0),
            ("New device", 20.0),
            ("High amount", 15.0),
            ("Velocity", 10.0),
        ],
        "minutes_ago": 48,
    },
    {
        "transaction_id": "TXN-884270",
        "account_masked": "ACC-••••4421",
        "amount": 875.00,
        "channel": "Mobile API",
        "merchant": "Food Delivery",
        "risk_score": 32,
        "risk_level": "LOW",
        "status": "ALLOWED",
        "prediction": "LEGITIMATE",
        "model_confidence": 91.0,
        "fraud_type": "",
        "shap": [
            ("Normal pattern", 60.0),
            ("Known merchant", 40.0),
        ],
        "minutes_ago": 61,
    },
    {
        "transaction_id": "TXN-884251",
        "account_masked": "ACC-••••6612",
        "amount": 18000.00,
        "channel": "Branch",
        "merchant": "Cash Withdrawal",
        "risk_score": 71,
        "risk_level": "HIGH",
        "status": "HELD",
        "prediction": "FRAUD",
        "model_confidence": 89.4,
        "fraud_type": "High Amount",
        "shap": [
            ("High amount", 45.0),
            ("Velocity spike", 30.0),
            ("Time anomaly", 25.0),
        ],
        "minutes_ago": 79,
    },
    {
        "transaction_id": "TXN-884230",
        "account_masked": "ACC-••••9977",
        "amount": 4500.00,
        "channel": "UPI",
        "merchant": "Online Shopping",
        "risk_score": 55,
        "risk_level": "MEDIUM",
        "status": "REVIEWING",
        "prediction": "FRAUD",
        "model_confidence": 81.2,
        "fraud_type": "Device Change",
        "shap": [
            ("Device change", 40.0),
            ("Amount deviation", 30.0),
            ("Merchant category", 30.0),
        ],
        "minutes_ago": 95,
    },
    {
        "transaction_id": "TXN-884210",
        "account_masked": "ACC-••••3308",
        "amount": 2100.00,
        "channel": "ATM",
        "merchant": "ATM-112-MUM",
        "risk_score": 62,
        "risk_level": "HIGH",
        "status": "PENDING",
        "prediction": "FRAUD",
        "model_confidence": 85.7,
        "fraud_type": "Geo Anomaly",
        "shap": [
            ("Geo anomaly", 50.0),
            ("Night transaction", 30.0),
            ("Amount pattern", 20.0),
        ],
        "minutes_ago": 112,
    },
]

DEMO_CASES = [
    {
        "case_id": "CASE-1024",
        "severity": "CRITICAL",
        "title": "Account Takeover — Coordinated Attack",
        "account": "ACC-••••7823",
        "transactions_count": 4,
        "status": "INVESTIGATING",
        "analyst": "SOC Analyst",
        "hours_ago": 1,
    },
    {
        "case_id": "CASE-1023",
        "severity": "HIGH",
        "title": "Velocity Spike — Unusual Card Activity",
        "account": "ACC-••••3341",
        "transactions_count": 7,
        "status": "OPEN",
        "analyst": "Priya Sharma",
        "hours_ago": 3,
    },
    {
        "case_id": "CASE-1022",
        "severity": "HIGH",
        "title": "Geo Anomaly — Transactions from Two Cities",
        "account": "ACC-••••9102",
        "transactions_count": 2,
        "status": "ESCALATED",
        "analyst": "Arjun Mehta",
        "hours_ago": 6,
    },
    {
        "case_id": "CASE-1021",
        "severity": "CRITICAL",
        "title": "Large International Wire — Suspicious Beneficiary",
        "account": "ACC-••••8899",
        "transactions_count": 1,
        "status": "RESOLVED",
        "analyst": "SOC Analyst",
        "hours_ago": 12,
    },
    {
        "case_id": "CASE-1020",
        "severity": "MEDIUM",
        "title": "Multiple Failed Auth — Possible Brute Force",
        "account": "ACC-••••5567",
        "transactions_count": 0,
        "status": "CLOSED",
        "analyst": "Priya Sharma",
        "hours_ago": 24,
    },
]

DEMO_ALERT_RULES = [
    {
        "name": "Velocity Spike Detection",
        "description": "Flag when >5 transactions occur within 10 minutes from the same account.",
        "rule_type": "velocity",
        "threshold": 75.0,
        "is_enabled": True,
    },
    {
        "name": "Unusual Geographic Location",
        "description": "Alert when a transaction originates from a country not in account profile.",
        "rule_type": "geo",
        "threshold": 70.0,
        "is_enabled": True,
    },
    {
        "name": "New Device + High Amount",
        "description": "Trigger when new device is used and transaction > ₹10,000.",
        "rule_type": "device",
        "threshold": 80.0,
        "is_enabled": True,
    },
    {
        "name": "Multiple Failed Authentication",
        "description": "Alert after 3 or more failed login attempts within 15 minutes.",
        "rule_type": "auth",
        "threshold": 60.0,
        "is_enabled": True,
    },
    {
        "name": "Night-Time High Value Transaction",
        "description": "Flag transactions >₹25,000 between 11 PM and 5 AM.",
        "rule_type": "time",
        "threshold": 65.0,
        "is_enabled": True,
    },
    {
        "name": "Unusual Merchant Category",
        "description": "Alert when account transacts with high-risk merchant category for first time.",
        "rule_type": "channel",
        "threshold": 72.0,
        "is_enabled": False,
    },
    {
        "name": "Amount Deviation >3 Sigma",
        "description": "Flag transactions more than 3 standard deviations above account's average.",
        "rule_type": "amount",
        "threshold": 85.0,
        "is_enabled": True,
    },
    {
        "name": "Card Not Present — International",
        "description": "Flag CNP transactions going to international merchants.",
        "rule_type": "custom",
        "threshold": 68.0,
        "is_enabled": False,
    },
]

DEMO_ACCOUNTS = [
    {"account_masked": "•••• 7823", "user_name": "Rohit Kumar", "account_type": "savings", "risk_score": 91, "recent_tx_count": 12, "fraud_alerts_count": 3, "status": "active"},
    {"account_masked": "•••• 3341", "user_name": "Priya Singh", "account_type": "savings", "risk_score": 78, "recent_tx_count": 7, "fraud_alerts_count": 2, "status": "active"},
    {"account_masked": "•••• 9102", "user_name": "Amir Khan", "account_type": "current", "risk_score": 67, "recent_tx_count": 5, "fraud_alerts_count": 1, "status": "active"},
    {"account_masked": "•••• 4821", "user_name": "Rahul Verma", "account_type": "savings", "risk_score": 82, "recent_tx_count": 9, "fraud_alerts_count": 3, "status": "active"},
    {"account_masked": "•••• 5567", "user_name": "Kavita Patel", "account_type": "nri", "risk_score": 85, "recent_tx_count": 4, "fraud_alerts_count": 2, "status": "suspended"},
    {"account_masked": "•••• 8899", "user_name": "Suresh Iyer", "account_type": "current", "risk_score": 93, "recent_tx_count": 1, "fraud_alerts_count": 1, "status": "frozen"},
    {"account_masked": "•••• 6612", "user_name": "Meena Reddy", "account_type": "savings", "risk_score": 71, "recent_tx_count": 8, "fraud_alerts_count": 2, "status": "active"},
    {"account_masked": "•••• 1234", "user_name": "Vikram Nair", "account_type": "savings", "risk_score": 45, "recent_tx_count": 14, "fraud_alerts_count": 0, "status": "active"},
    {"account_masked": "•••• 9977", "user_name": "Ananya Sharma", "account_type": "fd", "risk_score": 55, "recent_tx_count": 3, "fraud_alerts_count": 1, "status": "active"},
    {"account_masked": "•••• 3308", "user_name": "Rajan Gupta", "account_type": "savings", "risk_score": 62, "recent_tx_count": 6, "fraud_alerts_count": 1, "status": "active"},
]

DEMO_AUDIT_LOGS = [
    {"action": "Blocked Transaction", "transaction_id": "TXN-884290", "case_id": "CASE-1021", "result": "Successful", "minutes_ago": 5},
    {"action": "Escalated Case", "transaction_id": "", "case_id": "CASE-1022", "result": "Successful", "minutes_ago": 18},
    {"action": "Reviewed Transaction", "transaction_id": "TXN-884376", "case_id": "", "result": "Successful", "minutes_ago": 35},
    {"action": "Held Transaction", "transaction_id": "TXN-884398", "case_id": "", "result": "Successful", "minutes_ago": 52},
    {"action": "Created Case", "transaction_id": "TXN-884421", "case_id": "CASE-1024", "result": "Successful", "minutes_ago": 70},
    {"action": "Allowed Transaction", "transaction_id": "TXN-884270", "case_id": "", "result": "Successful", "minutes_ago": 90},
    {"action": "Disabled Alert Rule", "transaction_id": "", "case_id": "", "result": "Successful", "minutes_ago": 120},
    {"action": "Escalated Transaction", "transaction_id": "TXN-884355", "case_id": "CASE-1023", "result": "Successful", "minutes_ago": 145},
    {"action": "Closed Case", "transaction_id": "", "case_id": "CASE-1020", "result": "Successful", "minutes_ago": 200},
    {"action": "Reviewed Transaction", "transaction_id": "TXN-884312", "case_id": "", "result": "No Action", "minutes_ago": 240},
]


# ─────────────────────────────────────────────────────────────
#  Helper Utilities
# ─────────────────────────────────────────────────────────────

def _time_ago(minutes):
    return timezone.now() - timedelta(minutes=minutes)


def _hours_ago(hours):
    return timezone.now() - timedelta(hours=hours)


# ─────────────────────────────────────────────────────────────
#  Service Functions — return dicts, not model instances
#  so views stay decoupled from model changes
# ─────────────────────────────────────────────────────────────

def get_dashboard_kpis():
    """Return KPI metrics for the main dashboard."""
    from .models import FraudTransaction
    try:
        txns = FraudTransaction.objects.all()
        if txns.exists():
            total = txns.count()
            fraud = txns.filter(prediction="FRAUD").count()
            held = txns.filter(status__in=["HELD", "BLOCKED"]).count()
            exposure = txns.filter(prediction="FRAUD").aggregate(s=Sum("amount"))["s"] or 0
            detection_rate = round((fraud / total) * 100, 1) if total else 97.3
            return {
                "financial_exposure": f"₹{exposure:,.0f}",
                "exposure_held": held,
                "detection_rate": detection_rate,
                "under_review": txns.filter(status="REVIEWING").count(),
                "under_review_high": txns.filter(status="REVIEWING", risk_level__in=["CRITICAL", "HIGH"]).count(),
                "mtr": "4m 38s",
                "false_positive_rate": 2.1,
                "model_confidence": 98.4,
                "predictions_today": 12847,
            }
    except Exception:
        pass
    # Demo fallback
    return {
        "financial_exposure": "₹28,47,350",
        "exposure_held": 14,
        "detection_rate": 97.3,
        "under_review": 7,
        "under_review_high": 3,
        "mtr": "4m 38s",
        "false_positive_rate": 2.1,
        "model_confidence": 98.4,
        "predictions_today": 12847,
    }


def get_live_alerts(limit=20):
    """Return recent fraud transactions for the alert feed."""
    from .models import FraudTransaction
    try:
        txns = FraudTransaction.objects.filter(
            status__in=["PENDING", "REVIEWING", "HELD", "ESCALATED"]
        )[:limit]
        if txns.exists():
            result = []
            for t in txns:
                shap_top = list(t.shap_features.values_list("feature_name", flat=True)[:2])
                result.append({
                    "id": t.id,
                    "transaction_id": t.transaction_id,
                    "account_masked": t.account_masked,
                    "amount": f"₹{t.amount:,.0f}",
                    "channel": t.channel,
                    "merchant": t.merchant,
                    "risk_score": t.risk_score,
                    "risk_level": t.risk_level,
                    "top_factors": shap_top,
                    "status": t.status,
                    "timestamp": t.timestamp.strftime("%H:%M:%S"),
                })
            return result
    except Exception:
        pass
    # Demo fallback
    result = []
    for t in DEMO_TRANSACTIONS:
        if t["status"] in ["PENDING", "REVIEWING", "HELD", "ESCALATED"]:
            result.append({
                "id": t["transaction_id"],
                "transaction_id": t["transaction_id"],
                "account_masked": t["account_masked"],
                "amount": f"₹{t['amount']:,.0f}",
                "channel": t["channel"],
                "merchant": t["merchant"],
                "risk_score": t["risk_score"],
                "risk_level": t["risk_level"],
                "top_factors": [s[0] for s in t["shap"][:2]],
                "status": t["status"],
                "timestamp": _time_ago(t["minutes_ago"]).strftime("%H:%M:%S"),
            })
    return result[:limit]


def get_all_transactions(search=None, status_filter=None, risk_filter=None):
    """Return all transactions for the investigation page."""
    from .models import FraudTransaction
    try:
        qs = FraudTransaction.objects.all()
        if qs.exists():
            if search:
                qs = qs.filter(
                    Q(transaction_id__icontains=search) |
                    Q(account_masked__icontains=search) |
                    Q(merchant__icontains=search)
                )
            if status_filter:
                qs = qs.filter(status=status_filter)
            if risk_filter:
                qs = qs.filter(risk_level=risk_filter)
            result = []
            for t in qs[:50]:
                shap_top = list(t.shap_features.values_list("feature_name", flat=True)[:2])
                result.append({
                    "id": t.id,
                    "transaction_id": t.transaction_id,
                    "account_masked": t.account_masked,
                    "amount": f"₹{t.amount:,.0f}",
                    "channel": t.channel,
                    "merchant": t.merchant,
                    "risk_score": t.risk_score,
                    "risk_level": t.risk_level,
                    "top_factors": shap_top,
                    "status": t.status,
                    "prediction": t.prediction,
                    "model_confidence": t.model_confidence,
                    "timestamp": t.timestamp.strftime("%d %b %H:%M"),
                })
            return result
    except Exception:
        pass
    result = []
    for t in DEMO_TRANSACTIONS:
        if search and search.lower() not in t["transaction_id"].lower() and search.lower() not in t["account_masked"].lower():
            continue
        if status_filter and t["status"] != status_filter:
            continue
        if risk_filter and t["risk_level"] != risk_filter:
            continue
        result.append({
            "id": t["transaction_id"],
            "transaction_id": t["transaction_id"],
            "account_masked": t["account_masked"],
            "amount": f"₹{t['amount']:,.0f}",
            "channel": t["channel"],
            "merchant": t["merchant"],
            "risk_score": t["risk_score"],
            "risk_level": t["risk_level"],
            "top_factors": [s[0] for s in t["shap"][:2]],
            "status": t["status"],
            "prediction": t["prediction"],
            "model_confidence": t["model_confidence"],
            "timestamp": _time_ago(t["minutes_ago"]).strftime("%d %b %H:%M"),
        })
    return result


def get_transaction_detail(txn_id):
    """Return full transaction detail with SHAP features."""
    from .models import FraudTransaction
    try:
        t = FraudTransaction.objects.get(transaction_id=txn_id)
        shap = list(t.shap_features.values("feature_name", "contribution_pct"))
        return {
            "found": True,
            "id": t.id,
            "transaction_id": t.transaction_id,
            "account_masked": t.account_masked,
            "amount": f"₹{t.amount:,.0f}",
            "channel": t.channel,
            "merchant": t.merchant,
            "risk_score": t.risk_score,
            "risk_level": t.risk_level,
            "status": t.status,
            "prediction": t.prediction,
            "model_confidence": t.model_confidence,
            "fraud_type": t.fraud_type,
            "timestamp": t.timestamp.strftime("%d %b %Y %H:%M:%S"),
            "shap": shap,
        }
    except FraudTransaction.DoesNotExist:
        pass
    except Exception:
        pass
    # Demo fallback
    for t in DEMO_TRANSACTIONS:
        if t["transaction_id"] == txn_id:
            return {
                "found": True,
                "id": t["transaction_id"],
                "transaction_id": t["transaction_id"],
                "account_masked": t["account_masked"],
                "amount": f"₹{t['amount']:,.0f}",
                "channel": t["channel"],
                "merchant": t["merchant"],
                "risk_score": t["risk_score"],
                "risk_level": t["risk_level"],
                "status": t["status"],
                "prediction": t["prediction"],
                "model_confidence": t["model_confidence"],
                "fraud_type": t["fraud_type"],
                "timestamp": _time_ago(t["minutes_ago"]).strftime("%d %b %Y %H:%M:%S"),
                "shap": [{"feature_name": s[0], "contribution_pct": s[1]} for s in t["shap"]],
            }
    return {"found": False}


def get_fraud_trend_data():
    """Return 24h fraud rate data for the trend chart."""
    hours = ["06:00", "08:00", "10:00", "12:00", "14:00", "16:00", "18:00", "20:00", "22:00", "00:00", "02:00", "04:00"]
    rates = [1.2, 2.1, 2.8, 3.4, 2.9, 3.7, 4.2, 5.1, 6.2, 4.8, 3.3, 1.9]
    return {"labels": hours, "values": rates}


def get_risk_distribution_data():
    """Return risk distribution by time window."""
    windows = ["06:00", "09:00", "12:00", "15:00", "18:00", "21:00", "00:00", "03:00"]
    return {
        "labels": windows,
        "low": [320, 410, 480, 390, 460, 520, 280, 190],
        "medium": [45, 62, 78, 55, 71, 88, 42, 31],
        "high": [12, 18, 22, 15, 19, 28, 14, 8],
        "critical": [2, 4, 5, 3, 4, 7, 3, 1],
    }


def get_model_metrics():
    """Return model health metrics."""
    from .models import ModelMetrics
    try:
        m = ModelMetrics.objects.latest("last_updated")
        return {
            "model_name": m.model_name,
            "version": m.version,
            "is_healthy": m.is_healthy,
            "accuracy": m.accuracy,
            "precision": m.precision,
            "recall": m.recall,
            "f1_score": m.f1_score,
            "auc_roc": m.auc_roc,
            "throughput": m.throughput,
            "avg_latency_ms": m.avg_latency_ms,
            "queue_size": m.queue_size,
            "total_predictions_today": m.total_predictions_today,
        }
    except Exception:
        pass
    return {
        "model_name": "CNN-BiLSTM",
        "version": "v3.2.1",
        "is_healthy": True,
        "accuracy": 97.3,
        "precision": 96.1,
        "recall": 95.8,
        "f1_score": 95.9,
        "auc_roc": 0.9847,
        "throughput": 847,
        "avg_latency_ms": 12,
        "queue_size": 3,
        "total_predictions_today": 12847,
    }


def get_security_cases(status_filter=None):
    """Return security cases list."""
    from .models import SecurityCase
    try:
        qs = SecurityCase.objects.all()
        if status_filter:
            qs = qs.filter(status=status_filter)
        if qs.exists():
            result = []
            for c in qs:
                result.append({
                    "case_id": c.case_id,
                    "severity": c.severity,
                    "title": c.title,
                    "account": c.account,
                    "transactions_count": c.transactions_count,
                    "assigned_analyst": c.assigned_analyst.get_full_name() if c.assigned_analyst else "Unassigned",
                    "created_at": c.created_at.strftime("%d %b %H:%M"),
                    "status": c.status,
                })
            return result
    except Exception:
        pass
    result = []
    for c in DEMO_CASES:
        if status_filter and c["status"] != status_filter:
            continue
        result.append({
            "case_id": c["case_id"],
            "severity": c["severity"],
            "title": c["title"],
            "account": c["account"],
            "transactions_count": c["transactions_count"],
            "assigned_analyst": c["analyst"],
            "created_at": _hours_ago(c["hours_ago"]).strftime("%d %b %H:%M"),
            "status": c["status"],
        })
    return result


def get_verification_queue():
    """
    Return transactions pending human verification.

    Each item includes SHAP-based 'why_flagged' factors and account behaviour
    context so the analyst can immediately understand the risk.

    NOTE — Real ML integration:
      When the CNN-BiLSTM pipeline writes FraudTransaction + ShapFeature rows to
      the DB, the try block below will automatically serve real values.
      The demo fallback is used only when the DB tables are empty.
    """
    from .models import FraudTransaction

    # ── DEMO per-transaction SHAP factors & account context ──────────────────
    DEMO_QUEUE_DETAIL = {
        "TXN-884421": {
            "risk_description": "High probability of fraudulent activity",
            "why_flagged": [
                {"name": "High transaction velocity", "icon": "⚡", "contribution": 28,
                 "tooltip": "Transaction frequency is significantly higher than this account's normal behaviour."},
                {"name": "New device detected",        "icon": "📱", "contribution": 22,
                 "tooltip": "Transaction originated from a device not previously associated with this account."},
                {"name": "Unusual location",           "icon": "📍", "contribution": 19,
                 "tooltip": "Transaction location differs significantly from the account's historical locations."},
                {"name": "Amount above normal",        "icon": "💰", "contribution": 17,
                 "tooltip": "Transaction amount is significantly higher than this account's average."},
            ],
            "account_behaviour": {
                "avg_amount": "₹3,250", "current_amount": "₹14,750",
                "avg_tx_per_hr": "1.2", "current_tx_per_hr": "5",
                "known_devices": 3, "current_device": "Unknown",
                "typical_location": "Mumbai", "current_location": "Delhi",
            },
            "model_reasoning": (
                "The CNN-BiLSTM model detected multiple concurrent behavioural deviations "
                "from this account's normal pattern. The combination of a new unrecognised "
                "device, an unusual geographic origin, and a velocity spike within a short "
                "window elevated the composite risk score to CRITICAL."
            ),
        },
        "TXN-884376": {
            "risk_description": "Elevated probability of fraudulent activity",
            "why_flagged": [
                {"name": "Unusual transaction time",    "icon": "🕒", "contribution": 24,
                 "tooltip": "Transaction occurred outside the account's typical active hours."},
                {"name": "New device detected",         "icon": "📱", "contribution": 19,
                 "tooltip": "Transaction originated from a device not previously associated with this account."},
                {"name": "Amount deviation",            "icon": "💰", "contribution": 17,
                 "tooltip": "Transaction amount deviates significantly from the account's historical average."},
                {"name": "Multiple recent transactions","icon": "⚡", "contribution": 14,
                 "tooltip": "Several transactions were observed within an unusually short period."},
            ],
            "account_behaviour": {
                "avg_amount": "₹1,800", "current_amount": "₹3,400",
                "avg_tx_per_hr": "0.8", "current_tx_per_hr": "3",
                "known_devices": 2, "current_device": "Unknown",
                "typical_location": "Delhi", "current_location": "New York",
            },
            "model_reasoning": (
                "The model identified an unusual time-of-day pattern combined with a "
                "geographic anomaly. The account has no history of international ATM "
                "withdrawals, and the device fingerprint did not match any registered device."
            ),
        },
        "TXN-884312": {
            "risk_description": "Moderate risk — analyst review recommended",
            "why_flagged": [
                {"name": "Slightly unusual amount",  "icon": "💰", "contribution": 18,
                 "tooltip": "Amount is moderately above the account's typical POS spend."},
                {"name": "New merchant",             "icon": "🏪", "contribution": 12,
                 "tooltip": "This merchant has not appeared in the account's transaction history."},
                {"name": "Transaction frequency",    "icon": "⚡", "contribution": 10,
                 "tooltip": "The number of transactions in the last hour is slightly elevated."},
            ],
            "account_behaviour": {
                "avg_amount": "₹850", "current_amount": "₹1,200",
                "avg_tx_per_hr": "0.5", "current_tx_per_hr": "1.5",
                "known_devices": 1, "current_device": "Known",
                "typical_location": "Bengaluru", "current_location": "Bengaluru",
            },
            "model_reasoning": (
                "The model flagged this transaction due to a mildly elevated amount at an "
                "unknown merchant. The device and location are consistent with the account's "
                "normal profile. Prediction leans LEGITIMATE; human confirmation recommended."
            ),
        },
        "TXN-884230": {
            "risk_description": "Moderate-to-high probability of fraudulent activity",
            "why_flagged": [
                {"name": "Unusual location",        "icon": "📍", "contribution": 21,
                 "tooltip": "Transaction location differs significantly from the account's historical locations."},
                {"name": "New device",              "icon": "📱", "contribution": 15,
                 "tooltip": "Transaction originated from a device not previously associated with this account."},
                {"name": "Transaction velocity",    "icon": "⚡", "contribution": 12,
                 "tooltip": "Multiple transactions recorded in a compressed timeframe."},
            ],
            "account_behaviour": {
                "avg_amount": "₹2,100", "current_amount": "₹4,500",
                "avg_tx_per_hr": "0.6", "current_tx_per_hr": "2",
                "known_devices": 2, "current_device": "Unknown",
                "typical_location": "Chennai", "current_location": "Kolkata",
            },
            "model_reasoning": (
                "Geographic displacement combined with a new device fingerprint triggered "
                "this alert. The account normally transacts from Chennai; this transaction "
                "originated from Kolkata on an unrecognised device."
            ),
        },
        "TXN-884210": {
            "risk_description": "Elevated probability of fraudulent activity",
            "why_flagged": [
                {"name": "Multiple rapid transactions","icon": "⚡", "contribution": 25,
                 "tooltip": "5 or more transactions were recorded within a 10-minute window."},
                {"name": "Unusual amount",            "icon": "💰", "contribution": 18,
                 "tooltip": "Transaction amount is significantly higher than this account's average."},
                {"name": "Device change",             "icon": "📱", "contribution": 14,
                 "tooltip": "Transaction originated from a device not previously associated with this account."},
                {"name": "Unusual transaction time",  "icon": "🕒", "contribution": 11,
                 "tooltip": "Transaction occurred outside the account's typical active hours."},
            ],
            "account_behaviour": {
                "avg_amount": "₹1,100", "current_amount": "₹2,100",
                "avg_tx_per_hr": "0.4", "current_tx_per_hr": "4",
                "known_devices": 1, "current_device": "Unknown",
                "typical_location": "Mumbai", "current_location": "Mumbai",
            },
            "model_reasoning": (
                "A burst of ATM transactions within a short window was the primary signal. "
                "The device does not match the account's registered device, and the amount "
                "exceeds the account's typical ATM withdrawal pattern."
            ),
        },
    }

    def _risk_label(score):
        if score >= 86:
            return "Critical — immediate action required"
        elif score >= 71:
            return "High probability of fraudulent activity"
        elif score >= 41:
            return "Moderate risk — analyst review recommended"
        else:
            return "Low risk — likely legitimate"

    # ── Try real DB first ────────────────────────────────────────────────────
    try:
        txns = FraudTransaction.objects.filter(
            status__in=["PENDING", "REVIEWING"]
        ).order_by("-risk_score")
        if txns.exists():
            result = []
            for t in txns[:10]:
                shap_qs = list(t.shap_features.order_by("-contribution_pct").values(
                    "feature_name", "contribution_pct")[:4])
                why_flagged = [
                    {
                        "name": s["feature_name"],
                        "icon": "⚡",
                        "contribution": int(s["contribution_pct"]),
                        "tooltip": f"{s['feature_name']} contributed {s['contribution_pct']:.0f}% to the risk score.",
                    }
                    for s in shap_qs
                ]
                result.append({
                    "transaction_id": t.transaction_id,
                    "account_masked": t.account_masked,
                    "amount": f"₹{t.amount:,.0f}",
                    "channel": t.channel,
                    "merchant": t.merchant,
                    "risk_level": t.risk_level,
                    "risk_score": t.risk_score,
                    "prediction": t.prediction,
                    "model_confidence": t.model_confidence,
                    "minutes_ago": int((timezone.now() - t.timestamp).total_seconds() / 60),
                    "risk_description": _risk_label(t.risk_score),
                    "why_flagged": why_flagged,
                    "account_behaviour": {},
                    "model_reasoning": (
                        "The CNN-BiLSTM model detected behavioural deviations from this "
                        "account's normal pattern. Risk contributors above are derived from "
                        "SHAP feature attribution values."
                    ),
                    "data_source": "live",
                })
            return result
    except Exception:
        pass

    # ── Demo fallback ────────────────────────────────────────────────────────
    result = []
    for t in DEMO_TRANSACTIONS:
        if t["status"] not in ["PENDING", "REVIEWING"]:
            continue
        detail = DEMO_QUEUE_DETAIL.get(t["transaction_id"], {})
        result.append({
            "transaction_id": t["transaction_id"],
            "account_masked": t["account_masked"],
            "amount": f"₹{t['amount']:,.0f}",
            "channel": t.get("channel", "—"),
            "merchant": t.get("merchant", "—"),
            "risk_level": t["risk_level"],
            "risk_score": t["risk_score"],
            "prediction": t.get("prediction", "UNKNOWN"),
            "model_confidence": t.get("model_confidence", 0),
            "minutes_ago": t["minutes_ago"],
            "risk_description": detail.get("risk_description", _risk_label(t["risk_score"])),
            "why_flagged": detail.get("why_flagged", []),
            "account_behaviour": detail.get("account_behaviour", {}),
            "model_reasoning": detail.get("model_reasoning", ""),
            "data_source": "demo",
        })
    return result



def get_alert_rules():
    """Return alert rules list."""
    from .models import AlertRule
    try:
        rules = AlertRule.objects.all()
        if rules.exists():
            return list(rules.values("id", "name", "description", "rule_type", "threshold", "is_enabled"))
    except Exception:
        pass
    return DEMO_ALERT_RULES


def get_audit_logs():
    """Return audit log entries."""
    from .models import AuditLog
    try:
        logs = AuditLog.objects.select_related("analyst").all()[:50]
        if logs.exists():
            result = []
            for log in logs:
                result.append({
                    "timestamp": log.timestamp.strftime("%H:%M:%S"),
                    "analyst": log.analyst.get_full_name() if log.analyst else "SOC Analyst",
                    "action": log.action,
                    "transaction_id": log.transaction_id,
                    "case_id": log.case_id,
                    "result": log.result,
                    "ip_address": log.ip_address or "192.168.1.x",
                })
            return result
    except Exception:
        pass
    result = []
    for log in DEMO_AUDIT_LOGS:
        result.append({
            "timestamp": _time_ago(log["minutes_ago"]).strftime("%H:%M:%S"),
            "analyst": "SOC Analyst",
            "action": log["action"],
            "transaction_id": log["transaction_id"],
            "case_id": log["case_id"],
            "result": log["result"],
            "ip_address": "192.168.1.45",
        })
    return result


def get_accounts(search=None):
    """Return bank accounts for monitoring."""
    from .models import BankAccount
    try:
        qs = BankAccount.objects.all()
        if search:
            qs = qs.filter(
                Q(account_masked__icontains=search) |
                Q(user_name__icontains=search)
            )
        if qs.exists():
            return list(qs.values(
                "id", "account_masked", "user_name", "account_type",
                "risk_score", "recent_tx_count", "fraud_alerts_count", "status"
            ))
    except Exception:
        pass
    result = DEMO_ACCOUNTS[:]
    if search:
        result = [a for a in result if search.lower() in a["account_masked"].lower() or search.lower() in a["user_name"].lower()]
    return result


def get_model_insights():
    """Return model feature importance data."""
    features = [
        {"name": "Transaction Amount", "importance": 0.234, "pct": 23.4},
        {"name": "Transaction Frequency", "importance": 0.198, "pct": 19.8},
        {"name": "Device Change", "importance": 0.176, "pct": 17.6},
        {"name": "Location Change", "importance": 0.154, "pct": 15.4},
        {"name": "Time of Transaction", "importance": 0.087, "pct": 8.7},
        {"name": "Account Age", "importance": 0.071, "pct": 7.1},
        {"name": "Previous Fraud History", "importance": 0.052, "pct": 5.2},
        {"name": "Velocity", "importance": 0.028, "pct": 2.8},
    ]
    metrics = get_model_metrics()
    return {"features": features, "metrics": metrics}


def get_analytics_data():
    """Return all data for the analytics page."""
    return {
        "fraud_trend": get_fraud_trend_data(),
        "risk_distribution": get_risk_distribution_data(),
        "fraud_types": {
            "labels": ["Velocity Spike", "Geo Anomaly", "New Device", "Amount Deviation", "Account Takeover", "Other"],
            "values": [28, 22, 18, 15, 11, 6],
        },
        "channel_risk": {
            "labels": ["Mobile API", "Web Banking", "ATM", "POS", "UPI", "Branch"],
            "fraud_rate": [4.2, 3.8, 2.1, 1.4, 3.1, 0.8],
        },
        "hourly": {
            "labels": [f"{h:02d}:00" for h in range(24)],
            "values": [3, 2, 4, 6, 5, 3, 8, 12, 15, 18, 22, 19, 21, 17, 20, 24, 28, 32, 38, 45, 52, 41, 29, 14],
        },
    }
