from django.db import transaction

from .models import Toy, ToyStatusLog

ALLOWED_TRANSITIONS = {
    Toy.Status.INTAKE: {Toy.Status.AVAILABLE, Toy.Status.BROKEN},
    Toy.Status.AVAILABLE: {
        Toy.Status.RESERVED,
        Toy.Status.CHECKED_OUT,
        Toy.Status.BROKEN,
        Toy.Status.UNDER_REPAIR,
        Toy.Status.RETIRED,
    },
    Toy.Status.RESERVED: {Toy.Status.CHECKED_OUT, Toy.Status.AVAILABLE},
    Toy.Status.CHECKED_OUT: {
        Toy.Status.AVAILABLE,
        Toy.Status.RESERVED,
        Toy.Status.UNDER_REPAIR,
        Toy.Status.BROKEN,
        Toy.Status.OVERDUE,
    },
    Toy.Status.OVERDUE: {
        Toy.Status.AVAILABLE,
        Toy.Status.RESERVED,
        Toy.Status.CHECKED_OUT,
        Toy.Status.UNDER_REPAIR,
        Toy.Status.BROKEN,
    },
    Toy.Status.BROKEN: {Toy.Status.UNDER_REPAIR, Toy.Status.RETIRED},
    Toy.Status.UNDER_REPAIR: {Toy.Status.AVAILABLE, Toy.Status.RETIRED, Toy.Status.BROKEN},
    Toy.Status.RETIRED: set(),
}


@transaction.atomic
def transition_toy_status(toy, new_status, actor=None, reason="", related_object=None):
    current = toy.status
    if new_status == current:
        return toy
    allowed = ALLOWED_TRANSITIONS.get(current, set())
    if new_status not in allowed:
        raise ValueError(f"Cannot transition toy from {current} to {new_status}")

    ToyStatusLog.objects.create(
        toy=toy,
        from_status=current,
        to_status=new_status,
        changed_by=actor,
        reason=reason,
    )
    toy.status = new_status
    toy.save(update_fields=["status", "updated_at"])

    if new_status == Toy.Status.AVAILABLE:
        _try_claim_from_waitlist(toy)

    return toy


def _try_claim_from_waitlist(toy):
    from apps.waitlist.services import claim_next_waitlist_entry

    claim_next_waitlist_entry(toy)
