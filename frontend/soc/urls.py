from django.urls import path
from . import views

app_name = "soc"

urlpatterns = [
    # ── Main Pages ──────────────────────────────────────────
    path("", views.dashboard_view, name="dashboard"),
    path("transactions/", views.transactions_view, name="transactions"),
    path("alerts/", views.alerts_view, name="alerts"),
    path("analytics/", views.analytics_view, name="analytics"),
    path("cases/", views.cases_view, name="cases"),
    path("verification/", views.verification_view, name="verification"),
    path("users-accounts/", views.users_accounts_view, name="users_accounts"),
    path("audit-logs/", views.audit_logs_view, name="audit_logs"),
    path("reports/", views.reports_view, name="reports"),
    path("settings/", views.settings_view, name="settings"),

    # ── JSON API Endpoints ───────────────────────────────────
    path("api/dashboard-stats/", views.api_dashboard_stats, name="api_dashboard_stats"),
    path("api/alerts/", views.api_alerts, name="api_alerts"),
    path("api/transaction/<str:txn_id>/", views.api_transaction_detail, name="api_transaction_detail"),
    path("api/transaction/<str:txn_id>/action/", views.api_transaction_action, name="api_transaction_action"),
    path("api/alert-rule/<int:rule_id>/toggle/", views.api_toggle_alert_rule, name="api_toggle_alert_rule"),
]
