from datetime import timedelta

import pytest
from django.utils import timezone

from apps.checkouts import services as checkout_services
from apps.common.factories import MembershipFactory, ToyFactory, UserFactory
from apps.inventory.models import Toy
from apps.notifications.models import NotificationLog
from apps.reservations.models import Reservation

from .models import WaitlistEntry
from .services import claim_next_waitlist_entry, join_waitlist, leave_waitlist


@pytest.mark.django_db
def test_leave_waitlist_rejects_already_left_entry():
    entry = WaitlistEntry.objects.create(toy=ToyFactory(), user=UserFactory())
    leave_waitlist(entry)

    with pytest.raises(ValueError, match="Only active waitlist entries"):
        leave_waitlist(entry)


@pytest.mark.django_db
def test_claim_returns_none_when_no_entries():
    toy = ToyFactory(status=Toy.Status.AVAILABLE)

    result = claim_next_waitlist_entry(toy)

    assert result is None
    toy.refresh_from_db()
    assert toy.status == Toy.Status.AVAILABLE


@pytest.mark.django_db
def test_claim_returns_none_when_toy_not_actually_available():
    toy = ToyFactory(status=Toy.Status.CHECKED_OUT)
    join_waitlist(toy, UserFactory())

    result = claim_next_waitlist_entry(toy)

    assert result is None
    assert not Reservation.objects.exists()


@pytest.mark.django_db
def test_claim_creates_soft_hold_reservation_for_oldest_entry():
    toy = ToyFactory(status=Toy.Status.AVAILABLE)
    first_in_line = UserFactory()
    second_in_line = UserFactory()

    older_entry = join_waitlist(toy, first_in_line)
    older_entry.joined_at = timezone.now() - timedelta(hours=1)
    older_entry.save(update_fields=["joined_at"])
    join_waitlist(toy, second_in_line)

    reservation = claim_next_waitlist_entry(toy)

    assert reservation is not None
    assert reservation.user == first_in_line
    assert reservation.waitlist_entry == older_entry
    assert reservation.pickup_by_date == timezone.now().date() + timedelta(days=2)

    toy.refresh_from_db()
    assert toy.status == Toy.Status.RESERVED

    older_entry.refresh_from_db()
    assert older_entry.status == WaitlistEntry.Status.CONVERTED_TO_RESERVATION
    assert older_entry.converted_at is not None

    # second-in-line entry is untouched -- still waiting for the next opening
    remaining = WaitlistEntry.objects.get(user=second_in_line)
    assert remaining.status == WaitlistEntry.Status.WAITING


@pytest.mark.django_db
def test_claim_sends_waitlist_available_notification():
    toy = ToyFactory(status=Toy.Status.AVAILABLE)
    user = UserFactory()
    join_waitlist(toy, user)

    claim_next_waitlist_entry(toy)

    logs = NotificationLog.objects.filter(user=user, event_type="WAITLIST_AVAILABLE")
    assert logs.exists()
    assert "available" in logs.first().title.lower()


@pytest.mark.django_db
def test_claim_leaves_toy_available_when_no_waitlist_entry_exists_for_it():
    other_toy = ToyFactory(status=Toy.Status.AVAILABLE)
    waited_toy = ToyFactory(status=Toy.Status.AVAILABLE)
    join_waitlist(waited_toy, UserFactory())

    # a waitlist entry for a *different* toy must not be claimed here
    result = claim_next_waitlist_entry(other_toy)

    assert result is None
    other_toy.refresh_from_db()
    assert other_toy.status == Toy.Status.AVAILABLE


@pytest.mark.django_db
def test_returning_a_checked_out_toy_with_a_waitlist_auto_reserves_for_next_in_line():
    """End-to-end: staff return_checkout() -> transition_toy_status(AVAILABLE)
    -> waitlist auto-claim -> toy goes straight to RESERVED, never sitting in a
    plain AVAILABLE state another member could grab."""
    toy = ToyFactory(status=Toy.Status.AVAILABLE)
    staff = UserFactory(is_staff=True)

    borrower_membership = MembershipFactory()
    checkout = checkout_services.create_checkout(toy, borrower_membership.user, staff)

    waiting_user = UserFactory()
    entry = join_waitlist(toy, waiting_user)

    checkout_services.return_checkout(checkout, "LIGHTLY_USED", staff)

    toy.refresh_from_db()
    assert toy.status == Toy.Status.RESERVED

    entry.refresh_from_db()
    assert entry.status == WaitlistEntry.Status.CONVERTED_TO_RESERVATION

    reservation = Reservation.objects.get(waitlist_entry=entry)
    assert reservation.user == waiting_user
    assert reservation.status == Reservation.Status.ACTIVE


@pytest.mark.django_db
def test_returning_a_toy_with_no_waitlist_just_becomes_available():
    toy = ToyFactory(status=Toy.Status.AVAILABLE)
    staff = UserFactory(is_staff=True)
    membership = MembershipFactory()
    checkout = checkout_services.create_checkout(toy, membership.user, staff)

    checkout_services.return_checkout(checkout, "LIGHTLY_USED", staff)

    toy.refresh_from_db()
    assert toy.status == Toy.Status.AVAILABLE
    assert not Reservation.objects.exists()
