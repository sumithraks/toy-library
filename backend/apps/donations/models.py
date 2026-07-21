import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.common.models import TimeStampedModel


class Donor(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="donor_profiles",
    )
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)

    def __str__(self):
        return self.name


class Donation(TimeStampedModel):
    class Status(models.TextChoices):
        SUBMITTED = "SUBMITTED", "Submitted"
        ACCEPTED = "ACCEPTED", "Accepted"
        REJECTED = "REJECTED", "Rejected"
        IN_INTAKE = "IN_INTAKE", "In intake"
        COMPLETED = "COMPLETED", "Completed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    donor = models.ForeignKey(Donor, on_delete=models.CASCADE, related_name="donations")
    donated_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUBMITTED)
    rejection_reason = models.TextField(blank=True)

    def __str__(self):
        return f"Donation {self.id} ({self.status})"


class DonationItem(TimeStampedModel):
    class ItemType(models.TextChoices):
        BOARD_GAME = "BOARD_GAME", "Board game"
        PUZZLE = "PUZZLE", "Puzzle"
        RIDE_ON = "RIDE_ON", "Ride-on toy"
        BUILDING_SET = "BUILDING_SET", "Building set"
        SOFT_TOY = "SOFT_TOY", "Soft toy"
        DOLL = "DOLL", "Doll"
        OTHER = "OTHER", "Other"

    DISALLOWED_TYPES = {ItemType.SOFT_TOY, ItemType.DOLL}

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    donation = models.ForeignKey(Donation, on_delete=models.CASCADE, related_name="items")
    item_type = models.CharField(max_length=20, choices=ItemType.choices)
    description = models.TextField(blank=True)
    make = models.CharField(max_length=200, blank=True)
    model_name = models.CharField(max_length=200, blank=True)
    age_rating = models.CharField(max_length=64, blank=True)
    toy = models.OneToOneField(
        "inventory.Toy", on_delete=models.SET_NULL, null=True, blank=True, related_name="donation_item"
    )

    def clean(self):
        if self.item_type in self.DISALLOWED_TYPES:
            raise ValidationError(
                f"{self.get_item_type_display()} donations are not accepted (soft toys/dolls excluded)."
            )

    def __str__(self):
        return f"{self.item_type} - {self.donation_id}"


class DonationReceipt(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    donation = models.OneToOneField(Donation, on_delete=models.CASCADE, related_name="receipt")
    receipt_number = models.CharField(max_length=32, unique=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    pdf_file = models.FileField(upload_to="donation_receipts/", null=True, blank=True)
    summary_text = models.TextField(blank=True)

    def __str__(self):
        return self.receipt_number
