"""
SOC Dashboard Views
===================
All views are protected by @login_required + staff check.
"""
import json
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.contrib import messages
from django.utils import timezone

from . import services


def soc_required(view_func):
    """Decorator: require login + is_staff for all SOC views."""
    @login_required(login_url="/admin/login/")
    def wrapped(request, *args, **kwargs):
        if not request.user.is_staff:
            return render(request, "soc/403.html", status=403)
        return view_func(request, *args, **kwargs)
    wrapped.__name__ = view_func.__name__
    return wrapped


def soc_context(request, page_name):
    """Base context injected into every SOC template."""
    return {
        "page": page_name,
        "user": request.user,
        "now": timezone.now(),
        "model_metrics": services.get_model_metrics(),
    }


# ─────────────────────────────────────────────────────────────
#  Main Dashboard
# ─────────────────────────────────────────────────────────────

@soc_required
def dashboard_view(request):
    ctx = soc_context(request, "dashboard")
    ctx.update({
        "kpis": services.get_dashboard_kpis(),
        "alerts": services.get_live_alerts(limit=10),
        "fraud_trend": json.dumps(services.get_fraud_trend_data()),
        "risk_dist": json.dumps(services.get_risk_distribution_data()),
    })
    return render(request, "soc/dashboard.html", ctx)


# ─────────────────────────────────────────────────────────────
#  Transaction Investigation
# ─────────────────────────────────────────────────────────────

@soc_required
def transactions_view(request):
    search = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "")
    risk_filter = request.GET.get("risk", "")
    ctx = soc_context(request, "transactions")
    ctx.update({
        "transactions": services.get_all_transactions(search, status_filter or None, risk_filter or None),
        "search": search,
        "status_filter": status_filter,
        "risk_filter": risk_filter,
    })
    return render(request, "soc/transactions.html", ctx)


# ─────────────────────────────────────────────────────────────
#  Live Alerts
# ─────────────────────────────────────────────────────────────

@soc_required
def alerts_view(request):
    ctx = soc_context(request, "alerts")
    ctx["alerts"] = services.get_live_alerts(limit=20)
    return render(request, "soc/alerts.html", ctx)


# ─────────────────────────────────────────────────────────────
#  Risk Analytics
# ─────────────────────────────────────────────────────────────

@soc_required
def analytics_view(request):
    ctx = soc_context(request, "analytics")
    data = services.get_analytics_data()
    ctx.update({
        "fraud_trend": json.dumps(data["fraud_trend"]),
        "risk_dist": json.dumps(data["risk_distribution"]),
        "fraud_types": json.dumps(data["fraud_types"]),
        "channel_risk": json.dumps(data["channel_risk"]),
        "hourly": json.dumps(data["hourly"]),
    })
    return render(request, "soc/analytics.html", ctx)


# ─────────────────────────────────────────────────────────────
#  Model Health
# ─────────────────────────────────────────────────────────────

@soc_required
def model_health_view(request):
    ctx = soc_context(request, "model_health")
    ctx["metrics"] = services.get_model_metrics()
    return render(request, "soc/model_health.html", ctx)


# ─────────────────────────────────────────────────────────────
#  Security Cases
# ─────────────────────────────────────────────────────────────

@soc_required
def cases_view(request):
    status_filter = request.GET.get("status", "")
    ctx = soc_context(request, "cases")
    ctx.update({
        "cases": services.get_security_cases(status_filter or None),
        "status_filter": status_filter,
    })
    return render(request, "soc/cases.html", ctx)


# ─────────────────────────────────────────────────────────────
#  Verification Queue
# ─────────────────────────────────────────────────────────────

@soc_required
def verification_view(request):
    ctx = soc_context(request, "verification")
    ctx["queue"] = services.get_verification_queue()
    return render(request, "soc/verification.html", ctx)


# ─────────────────────────────────────────────────────────────
#  Users & Accounts
# ─────────────────────────────────────────────────────────────

@soc_required
def users_accounts_view(request):
    search = request.GET.get("q", "").strip()
    ctx = soc_context(request, "users_accounts")
    ctx.update({
        "accounts": services.get_accounts(search or None),
        "search": search,
    })
    return render(request, "soc/users_accounts.html", ctx)


# ─────────────────────────────────────────────────────────────
#  Model Insights
# ─────────────────────────────────────────────────────────────

@soc_required
def model_insights_view(request):
    ctx = soc_context(request, "model_insights")
    data = services.get_model_insights()
    ctx.update({
        "metrics": data["metrics"],
        "features": data["features"],
        "features_json": json.dumps(data["features"]),
    })
    return render(request, "soc/model_insights.html", ctx)


# ─────────────────────────────────────────────────────────────
#  Audit Logs
# ─────────────────────────────────────────────────────────────

@soc_required
def audit_logs_view(request):
    ctx = soc_context(request, "audit_logs")
    ctx["logs"] = services.get_audit_logs()
    return render(request, "soc/audit_logs.html", ctx)


# ─────────────────────────────────────────────────────────────
#  Reports
# ─────────────────────────────────────────────────────────────

@soc_required
def reports_view(request):
    ctx = soc_context(request, "reports")
    return render(request, "soc/reports.html", ctx)


# ─────────────────────────────────────────────────────────────
#  Alert Rules
# ─────────────────────────────────────────────────────────────

@soc_required
def alert_rules_view(request):
    ctx = soc_context(request, "alert_rules")
    ctx["rules"] = services.get_alert_rules()
    return render(request, "soc/alert_rules.html", ctx)


# ─────────────────────────────────────────────────────────────
#  Settings
# ─────────────────────────────────────────────────────────────

@soc_required
def settings_view(request):
    ctx = soc_context(request, "settings")
    return render(request, "soc/settings.html", ctx)


# ─────────────────────────────────────────────────────────────
#  JSON API Endpoints
# ─────────────────────────────────────────────────────────────

@login_required(login_url="/admin/login/")
@require_GET
def api_dashboard_stats(request):
    """JSON endpoint for polling dashboard KPIs."""
    if not request.user.is_staff:
        return JsonResponse({"error": "Forbidden"}, status=403)
    return JsonResponse({
        "kpis": services.get_dashboard_kpis(),
        "alerts": services.get_live_alerts(limit=10),
        "timestamp": timezone.now().strftime("%d %b %Y, %H:%M:%S"),
    })


@login_required(login_url="/admin/login/")
@require_GET
def api_alerts(request):
    """JSON endpoint for polling the live alert feed."""
    if not request.user.is_staff:
        return JsonResponse({"error": "Forbidden"}, status=403)
    return JsonResponse({"alerts": services.get_live_alerts(limit=20)})


@login_required(login_url="/admin/login/")
@require_GET
def api_transaction_detail(request, txn_id):
    """JSON endpoint for transaction detail + SHAP."""
    if not request.user.is_staff:
        return JsonResponse({"error": "Forbidden"}, status=403)
    return JsonResponse(services.get_transaction_detail(txn_id))


@login_required(login_url="/admin/login/")
@require_POST
def api_transaction_action(request, txn_id):
    """Handle ALLOW / HOLD / BLOCK / ESCALATE actions on a transaction."""
    if not request.user.is_staff:
        return JsonResponse({"error": "Forbidden"}, status=403)

    try:
        data = json.loads(request.body)
        action = data.get("action", "").upper()
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    valid_actions = {"ALLOW", "HOLD", "BLOCK", "ESCALATE"}
    if action not in valid_actions:
        return JsonResponse({"error": f"Invalid action. Must be one of: {', '.join(valid_actions)}"}, status=400)

    STATUS_MAP = {
        "ALLOW": "ALLOWED",
        "HOLD": "HELD",
        "BLOCK": "BLOCKED",
        "ESCALATE": "ESCALATED",
    }

    # Try to update real DB record
    try:
        from .models import FraudTransaction, AuditLog
        t = FraudTransaction.objects.get(transaction_id=txn_id)
        old_status = t.status
        t.status = STATUS_MAP[action]
        t.save()

        # Write audit log
        AuditLog.objects.create(
            analyst=request.user,
            action=f"{action.title()}d Transaction",
            transaction_id=txn_id,
            result="Successful",
            ip_address=request.META.get("REMOTE_ADDR"),
            session_id=request.session.session_key or "",
        )
        return JsonResponse({
            "success": True,
            "transaction_id": txn_id,
            "old_status": old_status,
            "new_status": STATUS_MAP[action],
            "action": action,
        })
    except Exception:
        pass

    # Demo mode — just return success
    return JsonResponse({
        "success": True,
        "transaction_id": txn_id,
        "new_status": STATUS_MAP[action],
        "action": action,
        "demo": True,
    })


@login_required(login_url="/admin/login/")
@require_POST
def api_toggle_alert_rule(request, rule_id):
    """Toggle an alert rule on/off."""
    if not request.user.is_staff:
        return JsonResponse({"error": "Forbidden"}, status=403)
    try:
        from .models import AlertRule
        rule = AlertRule.objects.get(pk=rule_id)
        rule.is_enabled = not rule.is_enabled
        rule.save()
        return JsonResponse({"success": True, "is_enabled": rule.is_enabled})
    except Exception:
        return JsonResponse({"success": True, "demo": True})
