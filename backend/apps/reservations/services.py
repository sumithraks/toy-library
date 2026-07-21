from datetime import datetime, time, timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.inventory.models import Toy
from apps.inventory.services import transition_toy_status

from .models import Reservation

RESERVATION_WINDOW_DAYS = 2


def _pickup_deadline_for(pickup_by_date):
    hour, minute = (int(x) for x in settings.LIBRARY_CLOSING_TIME.split(":"))
    naive = datetime.combine(pickup_by_date, time(hour=hour, minute=minute))
    return timezone.make_aware(naive) if timezone.is_naive(naive) else naive


@transaction.atomic
def create_reservation(toy, user, pickup_by_date, waitlist_entry=None):
    today = timezone.now().date()
    max_date = today + timedelta(days=RESERVATION_WINDOW_DAYS)
    if pickup_by_date > max_date:
        raise ValueError(f"pickup_by_date must be within {RESERVATION_WINDOW_DAYS} days")
    if pickup_by_date < today:
        raise ValueError("pickup_by_date cannot be in the past")

    if toy.status != Toy.Status.AVAILABLE:
        raise ValueError("Toy is not available to reserve")

    transition_toy_status(toy, Toy.Status.RESERVED, actor=user, reason="Reserved")

    reservation = Reservation.objects.create(
        toy=toy,
        user=user,
        pickup_by_date=pickup_by_date,
        pickup_deadline=_pickup_deadline_for(pickup_by_date),
        waitlist_entry=waitlist_entry,
        confirmation_sent_at=timezone.now(),
    )

    from apps.notifications.services import notify

    notify(
        user,
        event_type="RESERVATION_CONFIRMED",
        title=f"'{toy}' reserved for you",
        body=f"Pick it up by {reservation.pickup_deadline:%b %d, %I:%M %p}.",
        action_url=f"/reservations?highlight={reservation.id}",
    )
    return reservation


@transaction.atomic
def cancel_reservation(reservation, actor):
    if reservation.status != Reservation.Status.ACTIVE:
        raise ValueError("Only active reservations can be cancelled")
    reservation.status = Reservation.Status.CANCELLED
    reservation.save(update_fields=["status", "updated_at"])
    transition_toy_status(reservation.toy, Toy.Status.AVAILABLE, actor=actor, reason="Reservation cancelled")
    return reservation


@transaction.atomic
def confirm_pickup(reservation, staff_user):
    from apps.checkouts.services import create_checkout

    if reservation.status != Reservation.Status.ACTIVE:
        raise ValueError("Only active reservations can be picked up")

    checkout = create_checkout(reservation.toy, reservation.user, staff_user)

    reservation.status = Reservation.Status.PICKED_UP
    reservation.picked_up_at = timezone.now()
    reservation.resulting_checkout = checkout
    reservation.save(update_fields=["status", "picked_up_at", "resulting_checkout", "updated_at"])

    if reservation.waitlist_entry:
        from apps.waitlist.models import WaitlistEntry

        reservation.waitlist_entry.status = WaitlistEntry.Status.CONVERTED_TO_RESERVATION
        reservation.waitlist_entry.converted_at = timezone.now()
        reservation.waitlist_entry.save(update_fields=["status", "converted_at", "updated_at"])

    return reservation


@transaction.atomic
def expire_reservations():
    now = timezone.now()
    expired = Reservation.objects.select_related("toy").filter(
        status=Reservation.Status.ACTIVE, pickup_deadline__lt=now
    )
    for reservation in expired:
        reservation.status = Reservation.Status.EXPIRED
        reservation.save(update_fields=["status", "updated_at"])
        transition_toy_status(reservation.toy, Toy.Status.AVAILABLE, reason="Reservation pickup window expired")


def send_reservation_reminders():
    from apps.notifications.services import notify

    now = timezone.now()
    window_end = now + timedelta(hours=10)
    reservations = Reservation.objects.filter(
        status=Reservation.Status.ACTIVE,
        pickup_deadline__lte=window_end,
        pickup_deadline__gt=now,
        reminder_sent_at__isnull=True,
    ).select_related("toy", "user")
    for reservation in reservations:
        notify(
            reservation.user,
            event_type="RESERVATION_REMINDER",
            title=f"Reservation for '{reservation.toy}' ends soon",
            body=f"Pick it up by {reservation.pickup_deadline:%b %d, %I:%M %p} or it goes back on the shelf.",
            action_url=f"/reservations?highlight={reservation.id}",
        )
        reservation.reminder_sent_at = now
        reservation.save(update_fields=["reminder_sent_at", "updated_at"])
