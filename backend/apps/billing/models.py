import uuid

from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class LedgerEntry(TimeStampedModel):
    class EntryType(models.TextChoices):
        JOINING_FEE = "JOINING_FEE", "Joining fee"
        DEPOSIT = "DEPOSIT", "Deposit"
        RENEWAL_FEE = "RENEWAL_FEE", "Renewal fee"
        LATE_FEE = "LATE_FEE", "Late fee"
        PAID_EXTENSION_FEE = "PAID_EXTENSION_FEE", "Paid extension fee"
        DEPOSIT_REFUND = "DEPOSIT_REFUND", "Deposit refund"
        TIER_CHANGE_ADJUSTMENT = "TIER_CHANGE_ADJUSTMENT", "Tier change adjustment"
        OTHER = "OTHER", "Other"

    class Direction(models.TextChoices):
        CHARGE = "CHARGE", "Charge (user owes library)"
        CREDIT = "CREDIT", "Credit (library owes user)"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"
        WAIVED = "WAIVED", "Waived"
        CANCELLED = "CANCELLED", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ledger_entries"
    )
    entry_type = models.CharField(max_length=32, choices=EntryType.choices)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    direction = models.CharField(max_length=16, choices=Direction.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    due_date = models.DateField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    marked_paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ledger_entries_marked_paid",
    )
    notes = models.TextField(blank=True)

    related_checkout = models.ForeignKey(
        "checkouts.CheckoutRecord",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ledger_entries",
    )
    related_membership = models.ForeignKey(
        "memberships.Membership",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ledger_entries",
    )
    related_donation = models.ForeignKey(
        "donations.Donation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ledger_entries",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["entry_type", "status"]),
        ]

    def __str__(self):
        return f"{self.entry_type} {self.direction} ${self.amount} ({self.status}) - {self.user}"
