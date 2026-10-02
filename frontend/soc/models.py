"""
SOC Dashboard Models
====================
All models for the Security Operations Center dashboard.
These are separate from the existing portal app models.
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class RiskLevel(models.TextChoices):
    CRITICAL = "CRITICAL", "Critical"
    HIGH = "HIGH", "High"
    MEDIUM = "MEDIUM", "Medium"
    LOW = "LOW", "Low"


class TransactionStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    REVIEWING = "REVIEWING", "Reviewing"
    HELD = "HELD", "Held"
    BLOCKED = "BLOCKED", "Blocked"
    ALLOWED = "ALLOWED", "Allowed"
    ESCALATED = "ESCALATED", "Escalated"


class TransactionChannel(models.TextChoices):
    MOBILE_API = "Mobile API", "Mobile API"
    WEB_BANKING = "Web Banking", "Web Banking"
    ATM = "ATM", "ATM"
    BRANCH = "Branch", "Branch"
    POS = "POS", "POS"
    UPI = "UPI", "UPI"


class FraudTransaction(models.Model):
    """Core transaction record with fraud detection data."""
    transaction_id = models.CharField(max_length=32, unique=True)
    account_masked = models.CharField(max_length=20)  # e.g. ACC-••••7823
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    channel = models.CharField(max_length=32, choices=TransactionChannel.choices, default=TransactionChannel.MOBILE_API)
    merchant = models.CharField(max_length=128)
    risk_score = models.IntegerField(default=0)  # 0–100
    risk_level = models.CharField(max_length=10, choices=RiskLevel.choices, default=RiskLevel.LOW)
    status = models.CharField(max_length=16, choices=TransactionStatus.choices, default=TransactionStatus.PENDING)
    prediction = models.CharField(max_length=16, default="LEGITIMATE")  # FRAUD / LEGITIMATE
    model_confidence = models.FloatField(default=0.0)  # 0–100%
    fraud_type = models.CharField(max_length=64, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "Fraud Transaction"
        verbose_name_plural = "Fraud Transactions"

    def __str__(self):
        return f"{self.transaction_id} | {self.risk_level} | {self.status}"

    @property
    def amount_inr(self):
        return f"₹{self.amount:,.0f}"


class ShapFeature(models.Model):
    """SHAP-style feature contribution for a transaction."""
    transaction = models.ForeignKey(FraudTransaction, on_delete=models.CASCADE, related_name="shap_features")
    feature_name = models.CharField(max_length=64)
    contribution_pct = models.FloatField()  # e.g. 31.0 means +31%

    class Meta:
        ordering = ["-contribution_pct"]

    def __str__(self):
        return f"{self.feature_name}: {self.contribution_pct}%"


class CaseStatus(models.TextChoices):
    OPEN = "OPEN", "Open"
    INVESTIGATING = "INVESTIGATING", "Investigating"
    ESCALATED = "ESCALATED", "Escalated"
    RESOLVED = "RESOLVED", "Resolved"
    CLOSED = "CLOSED", "Closed"


class SecurityCase(models.Model):
    """A security investigation case that may link multiple transactions."""
    case_id = models.CharField(max_length=32, unique=True)
    severity = models.CharField(max_length=10, choices=RiskLevel.choices, default=RiskLevel.HIGH)
    title = models.CharField(max_length=256)
    account = models.CharField(max_length=32)
    transactions_count = models.IntegerField(default=1)
    assigned_analyst = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="cases"
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=16, choices=CaseStatus.choices, default=CaseStatus.OPEN)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.case_id} | {self.severity} | {self.status}"


class AlertRule(models.Model):
    """Configurable alert rules for fraud detection triggers."""
    RULE_TYPES = [
        ("velocity", "Velocity Spike"),
        ("geo", "Geographic Anomaly"),
        ("device", "New Device"),
        ("amount", "Amount Deviation"),
        ("auth", "Authentication Failure"),
        ("time", "Unusual Time"),
        ("channel", "Channel Mismatch"),
        ("custom", "Custom Rule"),
    ]
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    rule_type = models.CharField(max_length=16, choices=RULE_TYPES, default="custom")
    threshold = models.FloatField(default=70.0)  # risk score threshold
    is_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({'ON' if self.is_enabled else 'OFF'})"


class AuditLog(models.Model):
    """Audit trail of analyst actions on transactions and cases."""
    timestamp = models.DateTimeField(default=timezone.now)
    analyst = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="audit_logs")
    action = models.CharField(max_length=64)  # e.g. "Blocked Transaction"
    transaction_id = models.CharField(max_length=32, blank=True)
    case_id = models.CharField(max_length=32, blank=True)
    result = models.CharField(max_length=32, default="Successful")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    session_id = models.CharField(max_length=64, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.timestamp} | {self.analyst} | {self.action}"


class ModelMetrics(models.Model):
    """Snapshot of CNN-BiLSTM model health metrics."""
    model_name = models.CharField(max_length=64, default="CNN-BiLSTM")
    version = models.CharField(max_length=16, default="v3.2.1")
    accuracy = models.FloatField(default=97.3)
    precision = models.FloatField(default=96.1)
    recall = models.FloatField(default=95.8)
    f1_score = models.FloatField(default=95.9)
    auc_roc = models.FloatField(default=0.9847)
    throughput = models.IntegerField(default=847)  # predictions/min
    avg_latency_ms = models.IntegerField(default=12)
    queue_size = models.IntegerField(default=3)
    total_predictions_today = models.IntegerField(default=12847)
    is_healthy = models.BooleanField(default=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_updated"]
        verbose_name = "Model Metrics"
        verbose_name_plural = "Model Metrics"

    def __str__(self):
        return f"{self.model_name} {self.version} — AUC: {self.auc_roc}"


class BankAccount(models.Model):
    """Monitored bank accounts for the SOC."""
    ACCOUNT_TYPES = [
        ("savings", "Savings"),
        ("current", "Current"),
        ("nri", "NRI"),
        ("fd", "Fixed Deposit"),
    ]
    ACCOUNT_STATUS = [
        ("active", "Active"),
        ("suspended", "Suspended"),
        ("frozen", "Frozen"),
        ("closed", "Closed"),
    ]
    account_masked = models.CharField(max_length=20)  # e.g. •••• 4821
    user_name = models.CharField(max_length=128)
    account_type = models.CharField(max_length=16, choices=ACCOUNT_TYPES, default="savings")
    risk_score = models.IntegerField(default=0)
    recent_tx_count = models.IntegerField(default=0)
    fraud_alerts_count = models.IntegerField(default=0)
    status = models.CharField(max_length=16, choices=ACCOUNT_STATUS, default="active")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-risk_score"]

    def __str__(self):
        return f"{self.account_masked} | {self.user_name}"
