"""Complaint, notes, and status history models."""

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


def generate_complaint_reference() -> str:
    """Return next CMP-YYYY-NNNN reference for the current year (simple counter)."""
    year = timezone.now().year
    prefix = f"CMP-{year}-"
    latest = (
        Complaint.objects.filter(reference__startswith=prefix)
        .order_by("-reference")
        .values_list("reference", flat=True)
        .first()
    )
    if not latest:
        seq = 1
    else:
        try:
            seq = int(latest.rsplit("-", maxsplit=1)[-1]) + 1
        except ValueError:
            seq = Complaint.objects.filter(reference__startswith=prefix).count() + 1
    return f"{prefix}{seq:04d}"


class Complaint(models.Model):
    class Category(models.TextChoices):
        BILLING = "billing", "Billing"
        NETWORK = "network", "Network"
        DEVICE = "device", "Device"
        ROAMING = "roaming", "Roaming"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In Progress"
        ESCALATED = "escalated", "Escalated"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"

    reference = models.CharField(max_length=20, unique=True, db_index=True)
    customer_account = models.ForeignKey(
        "customers.CustomerAccount",
        on_delete=models.CASCADE,
        related_name="complaints",
    )
    category = models.CharField(max_length=30, choices=Category.choices, db_index=True)
    description = models.TextField()
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
    )
    assigned_agent = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_complaints",
        db_index=True,
    )
    escalation_reason = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["customer_account", "created_at"]),
            models.Index(fields=["assigned_agent", "status", "created_at"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["category", "status"]),
        ]

    def __str__(self):
        return self.reference

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = generate_complaint_reference()
        super().save(*args, **kwargs)


class ComplaintNote(models.Model):
    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name="notes",
    )
    author = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="complaint_notes",
    )
    body = models.TextField()
    is_internal = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["complaint", "created_at"]),
        ]

    def __str__(self):
        return f"Note on {self.complaint.reference}"


class ComplaintStatusHistory(models.Model):
    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name="status_history",
    )
    changed_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="complaint_status_changes",
    )
    from_status = models.CharField(max_length=30, blank=True)
    to_status = models.CharField(max_length=30)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["complaint", "created_at"]),
        ]
        verbose_name_plural = "Complaint status histories"

    def __str__(self):
        return f"{self.complaint.reference}: {self.from_status} → {self.to_status}"
