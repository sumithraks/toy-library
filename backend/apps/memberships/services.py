from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.billing.models import LedgerEntry
from apps.billing.services import create_ledger_entry, has_outstanding_charges, mark_paid

from .models import Membership, MembershipSignOff, MembershipTier, MembershipTierChange

RENEWAL_PERIOD_DAYS = 365


@transaction.atomic
def signup_membership(user, tier_code):
    if Membership.objects.filter(user=user, status=Membership.Status.ACTIVE).exists():
        raise ValueError("User already has an active membership")
    try:
        tier = MembershipTier.objects.get(code=tier_code, is_active=True)
    except MembershipTier.DoesNotExist:
        raise ValueError(f"No active membership tier with code {tier_code!r}")
    membership = Membership.objects.create(user=user, tier=tier, status=Membership.Status.PENDING_PAYMENT)
    create_ledger_entry(
        user=user,
        entry_type=LedgerEntry.EntryType.JOINING_FEE,
        amount=tier.joining_fee,
        direction=LedgerEntry.Direction.CHARGE,
        related_membership=membership,
        notes=f"Joining fee for {tier.name} membership",
    )
    create_ledger_entry(
        user=user,
        entry_type=LedgerEntry.EntryType.DEPOSIT,
        amount=tier.deposit_amount,
        direction=LedgerEntry.Direction.CHARGE,
        related_membership=membership,
        notes=f"Deposit for {tier.name} membership",
    )
    return membership


@transaction.atomic
def activate_membership(membership, staff_user):
    """Staff-run action once the joining fee + deposit have been collected in person."""
    if membership.status != Membership.Status.PENDING_PAYMENT:
        raise ValueError("Only PENDING_PAYMENT memberships can be activated")

    joining_fee_entry = LedgerEntry.objects.filter(
        related_membership=membership,
        entry_type=LedgerEntry.EntryType.JOINING_FEE,
        status=LedgerEntry.Status.PENDING,
    ).first()
    deposit_entry = LedgerEntry.objects.filter(
        related_membership=membership,
        entry_type=LedgerEntry.EntryType.DEPOSIT,
        status=LedgerEntry.Status.PENDING,
    ).first()
    if joining_fee_entry:
        mark_paid(joining_fee_entry, staff_user)
    if deposit_entry:
        mark_paid(deposit_entry, staff_user)

    membership.status = Membership.Status.ACTIVE
    membership.joined_at = timezone.now()
    membership.renewed_through = timezone.now().date() + timedelta(days=RENEWAL_PERIOD_DAYS)
    membership.deposit_ledger_entry = deposit_entry
    membership.save(update_fields=["status", "joined_at", "renewed_through", "deposit_ledger_entry", "updated_at"])
    return membership


def nudge_staff(membership):
    from apps.accounts.models import User
    from apps.notifications.services import notify

    if membership.status != Membership.Status.PENDING_PAYMENT:
        raise ValueError("Only memberships pending approval can be nudged")

    member_name = membership.user.get_full_name()
    for staff_user in User.objects.filter(is_staff=True, is_active=True):
        notify(
            staff_user,
            event_type="MEMBERSHIP_APPROVAL_REQUESTED",
            title="Membership awaiting approval",
            body=f"{member_name} is waiting for their {membership.tier.name} membership to be approved.",
            action_url="/admin/members",
        )
    return membership


@transaction.atomic
def change_tier(membership, new_tier, actor):
    if membership.status != Membership.Status.ACTIVE:
        raise ValueError("Only ACTIVE memberships can change tier")
    old_tier = membership.tier
    if old_tier.pk == new_tier.pk:
        raise ValueError("Membership is already on this tier")

    deposit_diff = new_tier.deposit_amount - old_tier.deposit_amount

    if deposit_diff > Decimal("0.00"):
        ledger_entry = create_ledger_entry(
            user=membership.user,
            entry_type=LedgerEntry.EntryType.TIER_CHANGE_ADJUSTMENT,
            amount=deposit_diff,
            direction=LedgerEntry.Direction.CHARGE,
            related_membership=membership,
            notes=f"Deposit top-up for upgrade {old_tier.code} -> {new_tier.code}",
        )
        MembershipTierChange.objects.create(
            membership=membership,
            from_tier=old_tier,
            to_tier=new_tier,
            changed_by=actor,
            deposit_adjustment_ledger_entry=ledger_entry,
        )
        # Tier does not change yet -- see confirm_tier_change_charge, applied on payment.
        return membership

    tier_change_kwargs = dict(membership=membership, from_tier=old_tier, to_tier=new_tier, changed_by=actor)
    if deposit_diff < Decimal("0.00"):
        ledger_entry = create_ledger_entry(
            user=membership.user,
            entry_type=LedgerEntry.EntryType.TIER_CHANGE_ADJUSTMENT,
            amount=abs(deposit_diff),
            direction=LedgerEntry.Direction.CREDIT,
            status=LedgerEntry.Status.PAID,
            related_membership=membership,
            notes=f"Deposit credit for downgrade {old_tier.code} -> {new_tier.code}",
        )
        tier_change_kwargs["deposit_adjustment_ledger_entry"] = ledger_entry

    MembershipTierChange.objects.create(**tier_change_kwargs)
    membership.tier = new_tier
    membership.save(update_fields=["tier", "updated_at"])
    return membership


@transaction.atomic
def confirm_tier_change_charge(ledger_entry):
    """Called by billing.services.mark_paid once a tier-upgrade deposit charge is paid."""
    tier_change = MembershipTierChange.objects.select_related("membership", "to_tier").get(
        deposit_adjustment_ledger_entry=ledger_entry
    )
    membership = tier_change.membership
    membership.tier = tier_change.to_tier
    membership.save(update_fields=["tier", "updated_at"])
    return membership


@transaction.atomic
def request_termination(membership, staff_user):
    from apps.checkouts.models import CheckoutRecord

    if membership.status != Membership.Status.ACTIVE:
        raise ValueError("Only ACTIVE memberships can have termination requested")

    if CheckoutRecord.objects.filter(
        member=membership.user, status__in=[CheckoutRecord.Status.ACTIVE, CheckoutRecord.Status.OVERDUE]
    ).exists():
        raise ValueError("Member has active or overdue checkouts; return all toys before termination")

    if has_outstanding_charges(membership.user):
        raise ValueError("Member has outstanding unpaid charges; settle balance before termination")

    deposit_due = (
        membership.deposit_ledger_entry.amount if membership.deposit_ledger_entry else membership.tier.deposit_amount
    )

    # membership.status == ACTIVE here, so any existing sign_off row can only be
    # REJECTED (approve/refund would have left the membership non-ACTIVE) -- reuse it.
    existing = getattr(membership, "sign_off", None)
    if existing is not None:
        sign_off = existing
        sign_off.status = MembershipSignOff.Status.REQUESTED
        sign_off.requested_at = timezone.now()
        sign_off.requested_by = staff_user
        sign_off.approved_at = None
        sign_off.approved_by = None
        sign_off.rejection_reason = ""
        sign_off.deposit_amount_due = deposit_due
        sign_off.save(
            update_fields=[
                "status",
                "requested_at",
                "requested_by",
                "approved_at",
                "approved_by",
                "rejection_reason",
                "deposit_amount_due",
                "updated_at",
            ]
        )
    else:
        sign_off = MembershipSignOff.objects.create(
            membership=membership,
            requested_by=staff_user,
            deposit_amount_due=deposit_due,
        )

    membership.status = Membership.Status.PENDING_TERMINATION
    membership.save(update_fields=["status", "updated_at"])
    return sign_off


@transaction.atomic
def approve_termination(sign_off, admin_user):
    if sign_off.status != MembershipSignOff.Status.REQUESTED:
        raise ValueError("Only REQUESTED termination requests can be approved")
    sign_off.status = MembershipSignOff.Status.APPROVED
    sign_off.approved_at = timezone.now()
    sign_off.approved_by = admin_user
    sign_off.save(update_fields=["status", "approved_at", "approved_by", "updated_at"])
    return sign_off


@transaction.atomic
def reject_termination(sign_off, admin_user, reason=""):
    if sign_off.status != MembershipSignOff.Status.REQUESTED:
        raise ValueError("Only REQUESTED termination requests can be rejected")
    sign_off.status = MembershipSignOff.Status.REJECTED
    sign_off.approved_at = timezone.now()
    sign_off.approved_by = admin_user
    sign_off.rejection_reason = reason
    sign_off.save(update_fields=["status", "approved_at", "approved_by", "rejection_reason", "updated_at"])

    membership = sign_off.membership
    membership.status = Membership.Status.ACTIVE
    membership.save(update_fields=["status", "updated_at"])
    return sign_off


@transaction.atomic
def refund_deposit(sign_off, staff_user, amount_returned, notes=""):
    if sign_off.status != MembershipSignOff.Status.APPROVED:
        raise ValueError("Only APPROVED termination requests can be refunded")

    if amount_returned < sign_off.deposit_amount_due and not notes:
        raise ValueError("notes is required when returning less than the full deposit")

    membership = sign_off.membership

    refund_entry = create_ledger_entry(
        user=membership.user,
        entry_type=LedgerEntry.EntryType.DEPOSIT_REFUND,
        amount=amount_returned,
        direction=LedgerEntry.Direction.CREDIT,
        status=LedgerEntry.Status.PAID,
        related_membership=membership,
        notes=notes,
    )

    sign_off.status = MembershipSignOff.Status.REFUNDED
    sign_off.processed_at = timezone.now()
    sign_off.processed_by = staff_user
    sign_off.deposit_amount_returned = amount_returned
    sign_off.deduction_reason = notes
    sign_off.refund_ledger_entry = refund_entry
    sign_off.save(
        update_fields=[
            "status",
            "processed_at",
            "processed_by",
            "deposit_amount_returned",
            "deduction_reason",
            "refund_ledger_entry",
            "updated_at",
        ]
    )

    membership.status = Membership.Status.DISCONTINUED
    membership.discontinued_at = timezone.now()
    membership.save(update_fields=["status", "discontinued_at", "updated_at"])
    return sign_off
