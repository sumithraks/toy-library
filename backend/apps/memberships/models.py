import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.common.models import TimeStampedModel


class MembershipTier(TimeStampedModel):
    class Code(models.TextChoices):
        SILVER = "SILVER", "Silver"
        PLATINUM = "PLATINUM", "Platinum"
        DIAMOND = "DIAMOND", "Diamond"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=16, choices=Code.choices, unique=True)
    name = models.CharField(max_length=64)
    joining_fee = models.DecimalField(max_digits=6, decimal_places=2)
    deposit_amount = models.DecimalField(max_digits=6, decimal_places=2)
    renewal_fee = models.DecimalField(max_digits=6, decimal_places=2)
    max_concurrent_checkouts = models.PositiveSmallIntegerField()
    loan_period_days = models.PositiveSmallIntegerField()
    complimentary_extension_days = models.PositiveSmallIntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["joining_fee"]

    def __str__(self):
        return self.name


class Membership(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING_PAYMENT = "PENDING_PAYMENT", "Pending payment"
        ACTIVE = "ACTIVE", "Active"
        PENDING_TERMINATION = "PENDING_TERMINATION", "Pending termination"
        DISCONTINUED = "DISCONTINUED", "Discontinued"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    tier = models.ForeignKey(MembershipTier, on_delete=models.PROTECT, related_name="memberships")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING_PAYMENT)
    joined_at = models.DateTimeField(null=True, blank=True)
    renewed_through = models.DateField(null=True, blank=True)
    discontinued_at = models.DateTimeField(null=True, blank=True)
    deposit_ledger_entry = models.ForeignKey(
        "billing.LedgerEntry",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(status="ACTIVE"),
                name="one_active_membership_per_user",
            )
        ]

    def __str__(self):
        return f"{self.user} - {self.tier} ({self.status})"


class MembershipTierChange(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    membership = models.ForeignKey(Membership, on_delete=models.CASCADE, related_name="tier_changes")
    from_tier = models.ForeignKey(
        MembershipTier, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    to_tier = models.ForeignKey(MembershipTier, on_delete=models.PROTECT, related_name="+")
    changed_at = models.DateTimeField(auto_now_add=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    deposit_adjustment_ledger_entry = models.ForeignKey(
        "billing.LedgerEntry", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    def __str__(self):
        return f"{self.membership} {self.from_tier}->{self.to_tier}"


class MembershipSignOff(TimeStampedModel):
    class Status(models.TextChoices):
        REQUESTED = "REQUESTED", "Requested"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        REFUNDED = "REFUNDED", "Refunded"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    membership = models.OneToOneField(Membership, on_delete=models.CASCADE, related_name="sign_off")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.REQUESTED)
    requested_at = models.DateTimeField(auto_now_add=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    rejection_reason = models.TextField(blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    deposit_amount_due = models.DecimalField(max_digits=6, decimal_places=2)
    deposit_amount_returned = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    deduction_reason = models.TextField(blank=True)
    refund_ledger_entry = models.ForeignKey(
        "billing.LedgerEntry", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    def __str__(self):
        return f"Sign-off for {self.membership} ({self.status})"
