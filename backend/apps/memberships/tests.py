from decimal import Decimal

import pytest

from apps.billing.models import LedgerEntry
from apps.billing.services import create_ledger_entry
from apps.checkouts import services as checkout_services
from apps.common.factories import MembershipFactory, MembershipTierFactory, ToyFactory, UserFactory
from apps.memberships import services
from apps.memberships.models import Membership, MembershipSignOff


@pytest.mark.django_db
def test_request_termination_blocked_by_active_checkout():
    membership = MembershipFactory()
    toy = ToyFactory()
    staff = UserFactory(is_staff=True)
    checkout_services.create_checkout(toy, membership.user, staff)

    with pytest.raises(ValueError, match="active or overdue checkouts"):
        services.request_termination(membership, staff)


@pytest.mark.django_db
def test_request_termination_blocked_by_outstanding_charge():
    membership = MembershipFactory()
    staff = UserFactory(is_staff=True)
    create_ledger_entry(
        user=membership.user,
        entry_type=LedgerEntry.EntryType.LATE_FEE,
        amount=Decimal("1.50"),
        direction=LedgerEntry.Direction.CHARGE,
    )

    with pytest.raises(ValueError, match="outstanding unpaid charges"):
        services.request_termination(membership, staff)


@pytest.mark.django_db
def test_request_termination_sets_pending_and_snapshots_deposit():
    membership = MembershipFactory()
    staff = UserFactory(is_staff=True)

    sign_off = services.request_termination(membership, staff)
    membership.refresh_from_db()

    assert membership.status == Membership.Status.PENDING_TERMINATION
    assert sign_off.status == MembershipSignOff.Status.REQUESTED
    assert sign_off.requested_by == staff
    assert sign_off.deposit_amount_due == membership.tier.deposit_amount


@pytest.mark.django_db
def test_request_termination_twice_is_rejected():
    membership = MembershipFactory()
    staff = UserFactory(is_staff=True)
    services.request_termination(membership, staff)

    with pytest.raises(ValueError, match="Only ACTIVE memberships"):
        services.request_termination(membership, staff)


@pytest.mark.django_db
def test_reject_termination_reverts_membership_and_allows_re_request():
    membership = MembershipFactory()
    staff = UserFactory(is_staff=True)
    admin = UserFactory(is_staff=True)
    sign_off = services.request_termination(membership, staff)

    sign_off = services.reject_termination(sign_off, admin, "Deposit dispute")
    membership.refresh_from_db()

    assert membership.status == Membership.Status.ACTIVE
    assert sign_off.status == MembershipSignOff.Status.REJECTED
    assert sign_off.rejection_reason == "Deposit dispute"

    # A rejected request can be re-submitted, reusing the same row.
    sign_off = services.request_termination(membership, staff)
    membership.refresh_from_db()
    assert membership.status == Membership.Status.PENDING_TERMINATION
    assert sign_off.status == MembershipSignOff.Status.REQUESTED


@pytest.mark.django_db
def test_approve_termination_requires_requested_status():
    membership = MembershipFactory()
    staff = UserFactory(is_staff=True)
    admin = UserFactory(is_staff=True)
    sign_off = services.request_termination(membership, staff)
    sign_off = services.approve_termination(sign_off, admin)

    with pytest.raises(ValueError, match="Only REQUESTED"):
        services.approve_termination(sign_off, admin)


@pytest.mark.django_db
def test_refund_deposit_requires_approved_status():
    membership = MembershipFactory()
    staff = UserFactory(is_staff=True)

    sign_off = services.request_termination(membership, staff)
    with pytest.raises(ValueError, match="Only APPROVED"):
        services.refund_deposit(sign_off, staff, Decimal("50.00"), "")


@pytest.mark.django_db
def test_refund_deposit_requires_notes_for_partial_refund():
    membership = MembershipFactory()
    staff = UserFactory(is_staff=True)
    admin = UserFactory(is_staff=True)
    sign_off = services.request_termination(membership, staff)
    sign_off = services.approve_termination(sign_off, admin)

    with pytest.raises(ValueError, match="notes is required"):
        services.refund_deposit(sign_off, staff, Decimal("30.00"), "")

    sign_off = services.refund_deposit(sign_off, staff, Decimal("30.00"), "Toy returned damaged")
    membership.refresh_from_db()
    assert membership.status == Membership.Status.DISCONTINUED
    assert sign_off.status == MembershipSignOff.Status.REFUNDED
    assert sign_off.deposit_amount_returned == Decimal("30.00")
    assert sign_off.refund_ledger_entry is not None


@pytest.mark.django_db
def test_change_tier_upgrade_charges_deposit_difference_and_defers_tier_change():
    silver = MembershipTierFactory(code="SILVER", deposit_amount=Decimal("50.00"))
    diamond = MembershipTierFactory(code="DIAMOND", deposit_amount=Decimal("80.00"))
    membership = MembershipFactory(tier=silver)
    staff = UserFactory(is_staff=True)

    services.change_tier(membership, diamond, staff)
    membership.refresh_from_db()

    # Tier does not change yet -- an upgrade charge is pending payment.
    assert membership.tier == silver
    pending_charge = membership.user.ledger_entries.get()
    assert pending_charge.amount == Decimal("30.00")
    assert pending_charge.status == LedgerEntry.Status.PENDING

    from apps.billing.services import mark_paid

    mark_paid(pending_charge, staff)
    membership.refresh_from_db()
    assert membership.tier == diamond


@pytest.mark.django_db
def test_change_tier_downgrade_credits_immediately():
    diamond = MembershipTierFactory(code="DIAMOND", deposit_amount=Decimal("80.00"))
    silver = MembershipTierFactory(code="SILVER", deposit_amount=Decimal("50.00"))
    membership = MembershipFactory(tier=diamond)
    staff = UserFactory(is_staff=True)

    services.change_tier(membership, silver, staff)
    membership.refresh_from_db()

    assert membership.tier == silver
    credit = membership.user.ledger_entries.get()
    assert credit.amount == Decimal("30.00")
    assert credit.direction == LedgerEntry.Direction.CREDIT
    assert credit.status == LedgerEntry.Status.PAID
