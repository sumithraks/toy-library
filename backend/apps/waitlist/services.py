from django.db import transaction
from django.utils import timezone

from .models import WaitlistEntry


def join_waitlist(toy, user):
    if WaitlistEntry.objects.filter(toy=toy, user=user, status=WaitlistEntry.Status.WAITING).exists():
        raise ValueError("Already on the waitlist for this toy")
    return WaitlistEntry.objects.create(toy=toy, user=user)


def leave_waitlist(entry):
    if entry.status != WaitlistEntry.Status.WAITING:
        raise ValueError("Only active waitlist entries can be cancelled")
    entry.status = WaitlistEntry.Status.CANCELLED
    entry.save(update_fields=["status", "updated_at"])
    return entry


@transaction.atomic
def claim_next_waitlist_entry(toy):
    """Called when a toy transitions to AVAILABLE. Auto-creates a soft-hold
    Reservation for the head-of-line waitlisted user, closing the race
    condition where another member could grab the toy first."""
    from apps.inventory.models import Toy
    from apps.reservations.services import create_reservation

    entry = (
        WaitlistEntry.objects.select_for_update(skip_locked=True)
        .filter(toy=toy, status=WaitlistEntry.Status.WAITING)
        .order_by("joined_at")
        .first()
    )
    if entry is None:
        return None

    toy.refresh_from_db()
    if toy.status != Toy.Status.AVAILABLE:
        return None

    pickup_by_date = timezone.now().date() + timezone.timedelta(days=2)
    reservation = create_reservation(toy, entry.user, pickup_by_date, waitlist_entry=entry)

    entry.status = WaitlistEntry.Status.CONVERTED_TO_RESERVATION
    entry.converted_at = timezone.now()
    entry.save(update_fields=["status", "converted_at", "updated_at"])

    from apps.notifications.services import notify

    notify(
        entry.user,
        event_type="WAITLIST_AVAILABLE",
        title=f"'{toy}' is available!",
        body=f"You're first in line. It's held for you until {reservation.pickup_deadline:%b %d, %I:%M %p}.",
        action_url=f"/reservations?highlight={reservation.id}",
    )
    return reservation
