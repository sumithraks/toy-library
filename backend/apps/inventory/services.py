from django.db import transaction
from django.utils import timezone

from .models import IntakeRecord, Toy, ToyStatusLog

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


@transaction.atomic
def intake_toy(
    *,
    model_name,
    make,
    condition,
    intake_type,
    staff_user,
    source=Toy.Source.PURCHASED,
    donation=None,
    age_rating_label="",
    description="",
    min_age_years=None,
    barcode_or_sku=None,
    notes="",
    reason="Intake completed",
):
    """Shared entry point for bringing a toy into the catalog, regardless of
    where it came from (donation, direct purchase, ...): creates the Toy
    record, logs an IntakeRecord for the assessment, and auto-transitions it
    to AVAILABLE (or BROKEN, if received damaged). Callers that need to
    associate the resulting toy with a source record (e.g. a donation item)
    do so with the returned toy's id.
    """
    toy = Toy.objects.create(
        model_name=model_name,
        make=make,
        min_age_years=min_age_years,
        age_rating_label=age_rating_label,
        description=description,
        condition=condition,
        source=source,
        donation=donation,
        barcode_or_sku=barcode_or_sku or None,
        status=Toy.Status.INTAKE,
    )
    IntakeRecord.objects.create(
        toy=toy,
        intake_type=intake_type,
        assessed_condition=condition,
        assessed_by=staff_user,
        notes=notes,
        completed_at=timezone.now(),
    )
    next_status = Toy.Status.BROKEN if condition == Toy.Condition.DAMAGED else Toy.Status.AVAILABLE
    transition_toy_status(toy, next_status, actor=staff_user, reason=reason)
    return toy


def intake_purchased_toy(
    *,
    model_name,
    make,
    condition,
    staff_user,
    age_rating_label="",
    description="",
    min_age_years=None,
    barcode_or_sku=None,
    notes="",
):
    return intake_toy(
        model_name=model_name,
        make=make,
        condition=condition,
        intake_type=IntakeRecord.IntakeType.INITIAL_PURCHASE,
        staff_user=staff_user,
        source=Toy.Source.PURCHASED,
        age_rating_label=age_rating_label,
        description=description,
        min_age_years=min_age_years,
        barcode_or_sku=barcode_or_sku,
        notes=notes,
        reason="Purchase intake completed",
    )
