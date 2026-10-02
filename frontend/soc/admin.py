"""
SOC Admin registrations
"""
from django.contrib import admin
from .models import (
    FraudTransaction, ShapFeature, SecurityCase,
    AlertRule, AuditLog, ModelMetrics, BankAccount
)


class ShapFeatureInline(admin.TabularInline):
    model = ShapFeature
    extra = 0


@admin.register(FraudTransaction)
class FraudTransactionAdmin(admin.ModelAdmin):
    list_display = ["transaction_id", "account_masked", "amount", "risk_level", "status", "timestamp"]
    list_filter = ["risk_level", "status", "channel"]
    search_fields = ["transaction_id", "account_masked", "merchant"]
    inlines = [ShapFeatureInline]
    ordering = ["-timestamp"]


@admin.register(SecurityCase)
class SecurityCaseAdmin(admin.ModelAdmin):
    list_display = ["case_id", "severity", "title", "account", "status", "assigned_analyst", "created_at"]
    list_filter = ["severity", "status"]
    search_fields = ["case_id", "title", "account"]


@admin.register(AlertRule)
class AlertRuleAdmin(admin.ModelAdmin):
    list_display = ["name", "rule_type", "threshold", "is_enabled"]
    list_filter = ["rule_type", "is_enabled"]


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["timestamp", "analyst", "action", "transaction_id", "case_id", "result"]
    list_filter = ["action", "result"]
    readonly_fields = ["timestamp"]


@admin.register(ModelMetrics)
class ModelMetricsAdmin(admin.ModelAdmin):
    list_display = ["model_name", "version", "accuracy", "auc_roc", "is_healthy", "last_updated"]


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ["account_masked", "user_name", "account_type", "risk_score", "fraud_alerts_count", "status"]
    list_filter = ["account_type", "status"]
    search_fields = ["account_masked", "user_name"]
