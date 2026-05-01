from django.contrib.auth.models import User
from django.db import models


class ServicePlan(models.Model):
    name = models.CharField(max_length=100, unique=True)
    monthly_price = models.DecimalField(max_digits=8, decimal_places=2)
    data_allowance_gb = models.DecimalField(max_digits=8, decimal_places=2)
    call_minutes = models.PositiveIntegerField()
    sms_allowance = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class CustomerAccount(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="customer_account",
    )
    account_number = models.CharField(max_length=30, unique=True, db_index=True)
    service_plan = models.ForeignKey(
        ServicePlan,
        on_delete=models.PROTECT,
        related_name="accounts",
    )
    current_balance = models.DecimalField(max_digits=10, decimal_places=2)
    region = models.CharField(max_length=100, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.account_number} ({self.user.username})"


class AccountUsage(models.Model):
    account = models.ForeignKey(
        CustomerAccount,
        on_delete=models.CASCADE,
        related_name="usage_records",
    )
    period_start = models.DateField()
    period_end = models.DateField()
    data_used_gb = models.DecimalField(max_digits=8, decimal_places=2)
    minutes_used = models.PositiveIntegerField(default=0)
    sms_used = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["account", "period_start", "period_end"]),
        ]

    def __str__(self):
        return f"{self.account_id} ({self.period_start}–{self.period_end})"


class Payment(models.Model):
    account = models.ForeignKey(
        CustomerAccount,
        on_delete=models.CASCADE,
        related_name="payments",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_at = models.DateTimeField(db_index=True)
    reference = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.reference
