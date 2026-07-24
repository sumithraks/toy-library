from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import Donation, DonationItem, DonationReceipt, Donor


@transaction.atomic
def submit_donation(donor_data, items_data, user=None):
    donor = Donor.objects.create(user=user, **donor_data)
    donation = Donation.objects.create(donor=donor)
    for item_data in items_data:
        item = DonationItem(donation=donation, **item_data)
        item.full_clean()
        item.save()
    return donation


@transaction.atomic
def accept_donation(donation, staff_user):
    if donation.status != Donation.Status.SUBMITTED:
        raise ValueError("Only SUBMITTED donations can be accepted")
    donation.status = Donation.Status.ACCEPTED
    donation.save(update_fields=["status", "updated_at"])
    _issue_receipt(donation)
    donation.status = Donation.Status.IN_INTAKE
    donation.save(update_fields=["status", "updated_at"])
    return donation


def reject_donation(donation, reason):
    if donation.status != Donation.Status.SUBMITTED:
        raise ValueError("Only SUBMITTED donations can be rejected")
    donation.status = Donation.Status.REJECTED
    donation.rejection_reason = reason
    donation.save(update_fields=["status", "rejection_reason", "updated_at"])
    return donation


def _issue_receipt(donation):
    year = timezone.now().year
    seq = DonationReceipt.objects.filter(receipt_number__startswith=f"DON-{year}-").count() + 1
    receipt_number = f"DON-{year}-{seq:06d}"
    summary_lines = [
        f"{item.item_type}: {item.make} {item.model_name} - {item.description}".strip()
        for item in donation.items.all()
    ]
    return DonationReceipt.objects.create(
        donation=donation,
        receipt_number=receipt_number,
        summary_text="\n".join(summary_lines),
    )


@transaction.atomic
def complete_item_intake(donation_item, staff_user, condition, age_rating="", notes=""):
    from apps.inventory.models import IntakeRecord, Toy
    from apps.inventory.services import intake_toy

    if donation_item.toy is not None:
        raise ValueError("This donation item already has an associated toy")

    donation = donation_item.donation
    if donation.status not in (Donation.Status.IN_INTAKE, Donation.Status.ACCEPTED):
        raise ValueError("Donation is not in an intake-eligible state")

    toy = intake_toy(
        model_name=donation_item.model_name or donation_item.item_type,
        make=donation_item.make,
        condition=condition,
        intake_type=IntakeRecord.IntakeType.DONATION,
        staff_user=staff_user,
        source=Toy.Source.DONATED,
        donation=donation,
        age_rating_label=age_rating or donation_item.age_rating,
        description=donation_item.description,
        notes=notes,
        reason="Donation intake completed",
    )

    # Track the donation by the toy id that intake_toy just added to inventory.
    donation_item.toy = toy
    donation_item.save(update_fields=["toy", "updated_at"])

    if not donation.items.filter(toy__isnull=True).exists():
        donation.status = Donation.Status.COMPLETED
        donation.save(update_fields=["status", "updated_at"])

    return toy
