import uuid

from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class CheckoutRecord(TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        RETURNED = "RETURNED", "Returned"
        OVERDUE = "OVERDUE", "Overdue"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    toy = models.ForeignKey("inventory.Toy", on_delete=models.PROTECT, related_name="checkouts")
    member = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="checkouts"
    )
    membership = models.ForeignKey(
        "memberships.Membership", on_delete=models.PROTECT, related_name="checkouts"
    )
    checked_out_at = models.DateTimeField(auto_now_add=True)
    checked_out_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    original_due_date = models.DateField()
    current_due_date = models.DateField()
    complimentary_extension_used = models.BooleanField(default=False)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    returned_at = models.DateTimeField(null=True, blank=True)
    returned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    return_condition = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ["-checked_out_at"]
        indexes = [
            models.Index(fields=["member", "status"]),
            models.Index(fields=["status", "current_due_date"]),
        ]

    def __str__(self):
        return f"{self.toy} -> {self.member} ({self.status})"


class Extension(TimeStampedModel):
    class ExtensionType(models.TextChoices):
        COMPLIMENTARY = "COMPLIMENTARY", "Complimentary"
        PAID = "PAID", "Paid"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    checkout = models.ForeignKey(CheckoutRecord, on_delete=models.CASCADE, related_name="extensions")
    extension_type = models.CharField(max_length=16, choices=ExtensionType.choices)
    requested_at = models.DateTimeField(auto_now_add=True)
    days_added = models.PositiveSmallIntegerField()
    previous_due_date = models.DateField()
    new_due_date = models.DateField()
    ledger_entry = models.ForeignKey(
        "billing.LedgerEntry", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    applied = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.extension_type} extension for {self.checkout}"


class LateFeeAssessment(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    checkout = models.ForeignKey(CheckoutRecord, on_delete=models.CASCADE, related_name="late_fee_assessments")
    assessed_at = models.DateField(auto_now_add=True)
    days_late_at_assessment = models.PositiveIntegerField()
    fee_amount = models.DecimalField(max_digits=8, decimal_places=2)
    ledger_entry = models.ForeignKey(
        "billing.LedgerEntry", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        ordering = ["-assessed_at"]

    def __str__(self):
        return f"Late fee for {self.checkout} - ${self.fee_amount}"
