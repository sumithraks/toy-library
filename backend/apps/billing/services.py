from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import LedgerEntry


def get_user_balance(user):
    """Positive = user owes the library. Negative = library owes the user."""
    entries = LedgerEntry.objects.filter(user=user, status=LedgerEntry.Status.PENDING)
    charges = sum(
        (e.amount for e in entries if e.direction == LedgerEntry.Direction.CHARGE),
        Decimal("0.00"),
    )
    credits = sum(
        (e.amount for e in entries if e.direction == LedgerEntry.Direction.CREDIT),
        Decimal("0.00"),
    )
    return charges - credits


def has_outstanding_charges(user):
    return LedgerEntry.objects.filter(
        user=user,
        status=LedgerEntry.Status.PENDING,
        direction=LedgerEntry.Direction.CHARGE,
    ).exists()


def create_ledger_entry(
    user,
    entry_type,
    amount,
    direction,
    status=LedgerEntry.Status.PENDING,
    due_date=None,
    notes="",
    related_checkout=None,
    related_membership=None,
    related_donation=None,
):
    return LedgerEntry.objects.create(
        user=user,
        entry_type=entry_type,
        amount=amount,
        direction=direction,
        status=status,
        due_date=due_date,
        notes=notes,
        related_checkout=related_checkout,
        related_membership=related_membership,
        related_donation=related_donation,
    )


@transaction.atomic
def mark_paid(ledger_entry, staff_user):
    if ledger_entry.status != LedgerEntry.Status.PENDING:
        raise ValueError("Only PENDING ledger entries can be marked paid")
    ledger_entry.status = LedgerEntry.Status.PAID
    ledger_entry.paid_at = timezone.now()
    ledger_entry.marked_paid_by = staff_user
    ledger_entry.save(update_fields=["status", "paid_at", "marked_paid_by", "updated_at"])

    # Side effects that depend on payment confirmation live in the owning app's
    # service layer to avoid billing depending on checkouts/memberships internals.
    from apps.checkouts.services import confirm_paid_extension
    from apps.memberships.services import confirm_tier_change_charge

    if ledger_entry.entry_type == LedgerEntry.EntryType.PAID_EXTENSION_FEE:
        confirm_paid_extension(ledger_entry)
    elif ledger_entry.entry_type == LedgerEntry.EntryType.TIER_CHANGE_ADJUSTMENT:
        confirm_tier_change_charge(ledger_entry)

    return ledger_entry
