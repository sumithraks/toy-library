from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.billing.models import LedgerEntry
from apps.billing.services import create_ledger_entry
from apps.inventory.models import Toy
from apps.inventory.services import transition_toy_status
from apps.memberships.models import Membership

from .models import CheckoutRecord, Extension, LateFeeAssessment

LATE_FEE_PER_DAY = Decimal("0.15")
PAID_EXTENSION_FEE_PER_DAY = Decimal("0.05")


def _deposit_cap_for_membership(membership):
    if membership.deposit_ledger_entry:
        return membership.deposit_ledger_entry.amount
    return membership.tier.deposit_amount


@transaction.atomic
def create_checkout(toy, member, staff_user):
    membership = Membership.objects.filter(user=member, status=Membership.Status.ACTIVE).first()
    if membership is None:
        raise ValueError("Member does not have an active membership")
    today = timezone.now().date()
    if membership.renewed_through and membership.renewed_through < today:
        raise ValueError("Membership has lapsed; renew before checking out")

    if toy.status not in (Toy.Status.AVAILABLE, Toy.Status.RESERVED):
        raise ValueError("Toy is not available for checkout")

    active_count = CheckoutRecord.objects.filter(
        member=member, status__in=[CheckoutRecord.Status.ACTIVE, CheckoutRecord.Status.OVERDUE]
    ).count()
    if active_count >= membership.tier.max_concurrent_checkouts:
        raise ValueError("Member has reached their tier's concurrent checkout limit")

    due_date = today + timedelta(days=membership.tier.loan_period_days)
    transition_toy_status(toy, Toy.Status.CHECKED_OUT, actor=staff_user, reason="Checked out")

    checkout = CheckoutRecord.objects.create(
        toy=toy,
        member=member,
        membership=membership,
        checked_out_by=staff_user,
        original_due_date=due_date,
        current_due_date=due_date,
    )
    return checkout


@transaction.atomic
def apply_complimentary_extension(checkout, actor):
    if checkout.status != CheckoutRecord.Status.ACTIVE:
        raise ValueError("Complimentary extension can only be filed while the checkout is active (not overdue)")
    if checkout.complimentary_extension_used:
        raise ValueError("Complimentary extension already used for this checkout")

    days = checkout.membership.tier.complimentary_extension_days
    previous_due = checkout.current_due_date
    new_due = previous_due + timedelta(days=days)

    Extension.objects.create(
        checkout=checkout,
        extension_type=Extension.ExtensionType.COMPLIMENTARY,
        days_added=days,
        previous_due_date=previous_due,
        new_due_date=new_due,
        applied=True,
    )
    checkout.complimentary_extension_used = True
    checkout.current_due_date = new_due
    checkout.save(update_fields=["complimentary_extension_used", "current_due_date", "updated_at"])
    return checkout


@transaction.atomic
def apply_paid_extension(checkout, days, actor):
    if checkout.status == CheckoutRecord.Status.RETURNED:
        raise ValueError("Cannot extend a returned checkout")

    previous_due = checkout.current_due_date
    new_due = previous_due + timedelta(days=days)
    amount = (Decimal(days) * PAID_EXTENSION_FEE_PER_DAY).quantize(Decimal("0.01"))

    ledger_entry = create_ledger_entry(
        user=checkout.member,
        entry_type=LedgerEntry.EntryType.PAID_EXTENSION_FEE,
        amount=amount,
        direction=LedgerEntry.Direction.CHARGE,
        related_checkout=checkout,
        notes=f"Paid extension of {days} day(s) for {checkout.toy}",
    )
    extension = Extension.objects.create(
        checkout=checkout,
        extension_type=Extension.ExtensionType.PAID,
        days_added=days,
        previous_due_date=previous_due,
        new_due_date=new_due,
        ledger_entry=ledger_entry,
        applied=False,
    )
    return extension


@transaction.atomic
def confirm_paid_extension(ledger_entry):
    """Called by billing.services.mark_paid once a paid-extension fee is paid."""
    extension = Extension.objects.select_related("checkout", "checkout__toy").get(ledger_entry=ledger_entry)
    checkout = extension.checkout
    checkout.current_due_date = extension.new_due_date

    today = timezone.now().date()
    if checkout.status == CheckoutRecord.Status.OVERDUE and extension.new_due_date >= today:
        checkout.status = CheckoutRecord.Status.ACTIVE
        if checkout.toy.status == Toy.Status.OVERDUE:
            transition_toy_status(checkout.toy, Toy.Status.CHECKED_OUT, reason="Paid extension cleared overdue status")

    checkout.save(update_fields=["current_due_date", "status", "updated_at"])
    extension.applied = True
    extension.save(update_fields=["applied", "updated_at"])
    return checkout


@transaction.atomic
def assess_late_fees():
    today = timezone.now().date()
    checkouts = CheckoutRecord.objects.select_related("membership", "toy", "membership__tier").filter(
        status__in=[CheckoutRecord.Status.ACTIVE, CheckoutRecord.Status.OVERDUE],
        current_due_date__lt=today,
    )
    for checkout in checkouts:
        if checkout.status == CheckoutRecord.Status.ACTIVE:
            checkout.status = CheckoutRecord.Status.OVERDUE
            checkout.save(update_fields=["status", "updated_at"])
            transition_toy_status(checkout.toy, Toy.Status.OVERDUE, reason="Due date passed")

        days_late = (today - checkout.current_due_date).days
        cap = _deposit_cap_for_membership(checkout.membership)
        fee_amount = min(Decimal(days_late) * LATE_FEE_PER_DAY, cap)

        ledger_entry = LedgerEntry.objects.filter(
            related_checkout=checkout,
            entry_type=LedgerEntry.EntryType.LATE_FEE,
            status=LedgerEntry.Status.PENDING,
        ).first()
        if ledger_entry:
            ledger_entry.amount = fee_amount
            ledger_entry.notes += f"\nDay {days_late} late: ${fee_amount} as of {today}"
            ledger_entry.save(update_fields=["amount", "notes", "updated_at"])
        else:
            ledger_entry = create_ledger_entry(
                user=checkout.member,
                entry_type=LedgerEntry.EntryType.LATE_FEE,
                amount=fee_amount,
                direction=LedgerEntry.Direction.CHARGE,
                related_checkout=checkout,
                notes=f"Day {days_late} late: ${fee_amount} as of {today}",
            )

        LateFeeAssessment.objects.create(
            checkout=checkout,
            days_late_at_assessment=days_late,
            fee_amount=fee_amount,
            ledger_entry=ledger_entry,
        )


@transaction.atomic
def return_checkout(checkout, condition, staff_user, damaged_status=None):
    if checkout.status not in (CheckoutRecord.Status.ACTIVE, CheckoutRecord.Status.OVERDUE):
        raise ValueError("Only active or overdue checkouts can be returned")

    checkout.status = CheckoutRecord.Status.RETURNED
    checkout.returned_at = timezone.now()
    checkout.returned_to = staff_user
    checkout.return_condition = condition
    checkout.save(update_fields=["status", "returned_at", "returned_to", "return_condition", "updated_at"])

    toy = checkout.toy
    if condition == Toy.Condition.DAMAGED:
        target = damaged_status or Toy.Status.UNDER_REPAIR
        if target not in (Toy.Status.UNDER_REPAIR, Toy.Status.BROKEN):
            raise ValueError("damaged_status must be UNDER_REPAIR or BROKEN")
        transition_toy_status(toy, target, actor=staff_user, reason="Returned damaged")
    else:
        toy.condition = condition
        toy.save(update_fields=["condition", "updated_at"])
        transition_toy_status(toy, Toy.Status.AVAILABLE, actor=staff_user, reason="Returned")

    return checkout
