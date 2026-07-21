from datetime import timedelta

import pytest
from django.utils import timezone
from freezegun import freeze_time

from apps.common.factories import MembershipFactory, ToyFactory, UserFactory
from apps.inventory.models import Toy
from apps.notifications.models import NotificationLog
from apps.waitlist.models import WaitlistEntry

from . import services
from .models import Reservation


@pytest.mark.django_db
class TestCreateReservation:
    def test_rejects_pickup_date_in_the_past(self):
        toy = ToyFactory()
        user = UserFactory()

        with pytest.raises(ValueError, match="cannot be in the past"):
            services.create_reservation(toy, user, timezone.now().date() - timedelta(days=1))


@pytest.mark.django_db
class TestCancelReservation:
    def test_cannot_cancel_a_non_active_reservation(self):
        toy = ToyFactory()
        user = UserFactory()
        reservation = services.create_reservation(toy, user, timezone.now().date())
        services.cancel_reservation(reservation, user)

        with pytest.raises(ValueError, match="Only active reservations"):
            services.cancel_reservation(reservation, user)


@pytest.mark.django_db
class TestConfirmPickup:
    def test_converts_linked_waitlist_entry(self):
        toy = ToyFactory()
        membership = MembershipFactory()
        user = membership.user
        staff = UserFactory(is_staff=True)
        waitlist_entry = WaitlistEntry.objects.create(toy=toy, user=user, status=WaitlistEntry.Status.WAITING)
        reservation = services.create_reservation(
            toy, user, timezone.now().date(), waitlist_entry=waitlist_entry
        )

        services.confirm_pickup(reservation, staff)

        waitlist_entry.refresh_from_db()
        assert waitlist_entry.status == WaitlistEntry.Status.CONVERTED_TO_RESERVATION
        assert waitlist_entry.converted_at is not None


@pytest.mark.django_db
class TestExpireReservations:
    def test_expires_past_deadline_reservations_and_frees_the_toy(self):
        toy = ToyFactory()
        user = UserFactory()
        reservation = services.create_reservation(toy, user, timezone.now().date())
        Reservation.objects.filter(id=reservation.id).update(
            pickup_deadline=timezone.now() - timedelta(hours=1)
        )

        services.expire_reservations()

        reservation.refresh_from_db()
        toy.refresh_from_db()
        assert reservation.status == Reservation.Status.EXPIRED
        assert toy.status == Toy.Status.AVAILABLE

    def test_leaves_reservations_within_deadline_untouched(self):
        # Frozen well before LIBRARY_CLOSING_TIME so the same-day pickup_deadline
        # computed by create_reservation is guaranteed to still be in the future.
        with freeze_time("2026-01-15 09:00:00"):
            toy = ToyFactory()
            user = UserFactory()
            reservation = services.create_reservation(toy, user, timezone.now().date())

            services.expire_reservations()

            reservation.refresh_from_db()
            assert reservation.status == Reservation.Status.ACTIVE


@pytest.mark.django_db
class TestSendReservationReminders:
    def test_sends_reminder_once_for_reservations_nearing_deadline(self):
        toy = ToyFactory()
        user = UserFactory()
        reservation = services.create_reservation(toy, user, timezone.now().date())
        Reservation.objects.filter(id=reservation.id).update(
            pickup_deadline=timezone.now() + timedelta(hours=5)
        )

        services.send_reservation_reminders()

        reservation.refresh_from_db()
        assert reservation.reminder_sent_at is not None
        assert NotificationLog.objects.filter(
            user=user, event_type="RESERVATION_REMINDER"
        ).exists()

        first_reminder_sent_at = reservation.reminder_sent_at
        services.send_reservation_reminders()
        reservation.refresh_from_db()
        assert reservation.reminder_sent_at == first_reminder_sent_at

    def test_skips_reservations_outside_the_reminder_window(self):
        toy = ToyFactory()
        user = UserFactory()
        reservation = services.create_reservation(toy, user, timezone.now().date())
        Reservation.objects.filter(id=reservation.id).update(
            pickup_deadline=timezone.now() + timedelta(hours=48)
        )

        services.send_reservation_reminders()

        reservation.refresh_from_db()
        assert reservation.reminder_sent_at is None
