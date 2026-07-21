from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.billing.models import LedgerEntry
from apps.billing.services import create_ledger_entry, mark_paid
from apps.checkouts import services
from apps.checkouts.models import CheckoutRecord
from apps.common.factories import MembershipFactory, MembershipTierFactory, ToyFactory, UserFactory
from apps.inventory.models import Toy
from apps.memberships.models import Membership


@pytest.mark.django_db
def test_create_checkout_succeeds_for_active_member():
    membership = MembershipFactory()
    toy = ToyFactory()
    staff = UserFactory(is_staff=True)

    checkout = services.create_checkout(toy, membership.user, staff)

    assert checkout.status == CheckoutRecord.Status.ACTIVE
    assert checkout.current_due_date == timezone.now().date() + timedelta(
        days=membership.tier.loan_period_days
    )
    toy.refresh_from_db()
    assert toy.status == Toy.Status.CHECKED_OUT


@pytest.mark.django_db
def test_create_checkout_rejects_lapsed_membership():
    membership = MembershipFactory(renewed_through=timezone.now().date() - timedelta(days=1))
    toy = ToyFactory()
    staff = UserFactory(is_staff=True)

    with pytest.raises(ValueError, match="lapsed"):
        services.create_checkout(toy, membership.user, staff)


@pytest.mark.django_db
def test_create_checkout_rejects_over_tier_limit():
    tier = MembershipTierFactory(code="SILVER", max_concurrent_checkouts=1)
    membership = MembershipFactory(tier=tier)
    staff = UserFactory(is_staff=True)
    toy1, toy2 = ToyFactory(), ToyFactory()

    services.create_checkout(toy1, membership.user, staff)

    with pytest.raises(ValueError, match="concurrent checkout limit"):
        services.create_checkout(toy2, membership.user, staff)


@pytest.mark.django_db
def test_complimentary_extension_blocked_once_overdue():
    membership = MembershipFactory()
    toy = ToyFactory()
    staff = UserFactory(is_staff=True)
    checkout = services.create_checkout(toy, membership.user, staff)

    checkout.status = CheckoutRecord.Status.OVERDUE
    checkout.save(update_fields=["status"])

    with pytest.raises(ValueError, match="active"):
        services.apply_complimentary_extension(checkout, membership.user)


@pytest.mark.django_db
def test_complimentary_extension_extends_from_current_due_date():
    tier = MembershipTierFactory(code="SILVER", complimentary_extension_days=2)
    membership = MembershipFactory(tier=tier)
    toy = ToyFactory()
    staff = UserFactory(is_staff=True)
    checkout = services.create_checkout(toy, membership.user, staff)
    original_due = checkout.current_due_date

    services.apply_complimentary_extension(checkout, membership.user)
    checkout.refresh_from_db()

    assert checkout.current_due_date == original_due + timedelta(days=2)
    assert checkout.complimentary_extension_used is True

    with pytest.raises(ValueError, match="already used"):
        services.apply_complimentary_extension(checkout, membership.user)


@pytest.mark.django_db
def test_late_fee_accrual_caps_at_deposit_amount():
    tier = MembershipTierFactory(code="SILVER", deposit_amount=Decimal("50.00"))
    membership = MembershipFactory(tier=tier)
    toy = ToyFactory()
    staff = UserFactory(is_staff=True)
    checkout = services.create_checkout(toy, membership.user, staff)

    # Simulate the checkout being extremely overdue (enough days to exceed the deposit cap).
    checkout.current_due_date = timezone.now().date() - timedelta(days=1000)
    checkout.save(update_fields=["current_due_date"])

    services.assess_late_fees()

    checkout.refresh_from_db()
    assert checkout.status == CheckoutRecord.Status.OVERDUE
    toy.refresh_from_db()
    assert toy.status == Toy.Status.OVERDUE

    late_fee_entry = checkout.ledger_entries.get()
    assert late_fee_entry.amount == Decimal("50.00")


@pytest.mark.django_db
def test_paid_extension_does_not_move_due_date_until_paid():
    membership = MembershipFactory()
    toy = ToyFactory()
    staff = UserFactory(is_staff=True)
    checkout = services.create_checkout(toy, membership.user, staff)
    original_due = checkout.current_due_date

    extension = services.apply_paid_extension(checkout, 5, membership.user)
    checkout.refresh_from_db()

    assert checkout.current_due_date == original_due
    assert extension.ledger_entry.amount == Decimal("0.25")

    mark_paid(extension.ledger_entry, staff)
    checkout.refresh_from_db()

    assert checkout.current_due_date == original_due + timedelta(days=5)


@pytest.mark.django_db
def test_create_checkout_rejects_member_without_membership():
    member = UserFactory()
    toy = ToyFactory()
    staff = UserFactory(is_staff=True)

    with pytest.raises(ValueError, match="does not have an active membership"):
        services.create_checkout(toy, member, staff)


@pytest.mark.django_db
def test_create_checkout_rejects_unavailable_toy():
    membership = MembershipFactory()
    toy = ToyFactory(status=Toy.Status.BROKEN)
    staff = UserFactory(is_staff=True)

    with pytest.raises(ValueError, match="not available for checkout"):
        services.create_checkout(toy, membership.user, staff)


@pytest.mark.django_db
def test_deposit_cap_uses_actual_deposit_paid_when_present():
    tier = MembershipTierFactory(code="SILVER", deposit_amount=Decimal("50.00"))
    membership = MembershipFactory(tier=tier)
    deposit_entry = create_ledger_entry(
        user=membership.user,
        entry_type=LedgerEntry.EntryType.DEPOSIT,
        amount=Decimal("30.00"),
        direction=LedgerEntry.Direction.CHARGE,
        status=LedgerEntry.Status.PAID,
    )
    membership.deposit_ledger_entry = deposit_entry
    membership.save(update_fields=["deposit_ledger_entry"])

    toy = ToyFactory()
    staff = UserFactory(is_staff=True)
    checkout = services.create_checkout(toy, membership.user, staff)
    checkout.current_due_date = timezone.now().date() - timedelta(days=1000)
    checkout.save(update_fields=["current_due_date"])

    services.assess_late_fees()

    late_fee_entry = checkout.ledger_entries.get(entry_type=LedgerEntry.EntryType.LATE_FEE)
    assert late_fee_entry.amount == Decimal("30.00")


@pytest.mark.django_db
def test_apply_paid_extension_rejects_returned_checkout():
    membership = MembershipFactory()
    toy = ToyFactory()
    staff = UserFactory(is_staff=True)
    checkout = services.create_checkout(toy, membership.user, staff)
    services.return_checkout(checkout, Toy.Condition.LIGHTLY_USED, staff)

    with pytest.raises(ValueError, match="Cannot extend a returned checkout"):
        services.apply_paid_extension(checkout, 3, membership.user)


@pytest.mark.django_db
def test_confirm_paid_extension_clears_overdue_status():
    membership = MembershipFactory()
    toy = ToyFactory()
    staff = UserFactory(is_staff=True)
    checkout = services.create_checkout(toy, membership.user, staff)
    checkout.current_due_date = timezone.now().date() - timedelta(days=5)
    checkout.save(update_fields=["current_due_date"])
    services.assess_late_fees()
    checkout.refresh_from_db()
    assert checkout.status == CheckoutRecord.Status.OVERDUE

    extension = services.apply_paid_extension(checkout, 10, membership.user)
    mark_paid(extension.ledger_entry, staff)

    checkout.refresh_from_db()
    toy.refresh_from_db()
    assert checkout.status == CheckoutRecord.Status.ACTIVE
    assert toy.status == Toy.Status.CHECKED_OUT


@pytest.mark.django_db
def test_assess_late_fees_updates_existing_pending_entry_on_repeat_runs():
    membership = MembershipFactory()
    toy = ToyFactory()
    staff = UserFactory(is_staff=True)
    checkout = services.create_checkout(toy, membership.user, staff)
    checkout.current_due_date = timezone.now().date() - timedelta(days=2)
    checkout.save(update_fields=["current_due_date"])

    services.assess_late_fees()
    services.assess_late_fees()

    entries = checkout.ledger_entries.filter(entry_type=LedgerEntry.EntryType.LATE_FEE)
    assert entries.count() == 1


@pytest.mark.django_db
def test_return_checkout_rejects_already_returned_checkout():
    membership = MembershipFactory()
    toy = ToyFactory()
    staff = UserFactory(is_staff=True)
    checkout = services.create_checkout(toy, membership.user, staff)
    services.return_checkout(checkout, Toy.Condition.LIGHTLY_USED, staff)

    with pytest.raises(ValueError, match="Only active or overdue checkouts can be returned"):
        services.return_checkout(checkout, Toy.Condition.LIGHTLY_USED, staff)


@pytest.mark.django_db
def test_return_checkout_rejects_invalid_damaged_status():
    membership = MembershipFactory()
    toy = ToyFactory()
    staff = UserFactory(is_staff=True)
    checkout = services.create_checkout(toy, membership.user, staff)

    with pytest.raises(ValueError, match="damaged_status must be"):
        services.return_checkout(checkout, Toy.Condition.DAMAGED, staff, damaged_status=Toy.Status.RETIRED)
