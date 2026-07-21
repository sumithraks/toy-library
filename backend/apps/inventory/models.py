import uuid

from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class Toy(TimeStampedModel):
    class Status(models.TextChoices):
        INTAKE = "INTAKE", "Intake"
        AVAILABLE = "AVAILABLE", "Available"
        RESERVED = "RESERVED", "Reserved"
        CHECKED_OUT = "CHECKED_OUT", "Checked out"
        OVERDUE = "OVERDUE", "Overdue"
        BROKEN = "BROKEN", "Broken"
        UNDER_REPAIR = "UNDER_REPAIR", "Under repair"
        RETIRED = "RETIRED", "Retired"

    class Condition(models.TextChoices):
        NEW = "NEW", "New"
        LIGHTLY_USED = "LIGHTLY_USED", "Lightly used"
        USED = "USED", "Used"
        DAMAGED = "DAMAGED", "Damaged"

    class Source(models.TextChoices):
        PURCHASED = "PURCHASED", "Purchased"
        DONATED = "DONATED", "Donated"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    model_name = models.CharField(max_length=200)
    make = models.CharField(max_length=200)
    min_age_years = models.PositiveSmallIntegerField(null=True, blank=True)
    age_rating_label = models.CharField(max_length=64, blank=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.INTAKE)
    condition = models.CharField(max_length=20, choices=Condition.choices, default=Condition.NEW)
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.PURCHASED)
    donation = models.ForeignKey(
        "donations.Donation", on_delete=models.SET_NULL, null=True, blank=True, related_name="toys"
    )
    image = models.ImageField(upload_to="toys/", null=True, blank=True)
    barcode_or_sku = models.CharField(max_length=64, unique=True, null=True, blank=True)
    retired_at = models.DateTimeField(null=True, blank=True)
    retired_reason = models.TextField(blank=True)

    class Meta:
        ordering = ["model_name"]
        indexes = [models.Index(fields=["status"])]

    def __str__(self):
        return f"{self.make} {self.model_name}"


class ToyStatusLog(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    toy = models.ForeignKey(Toy, on_delete=models.CASCADE, related_name="status_logs")
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20)
    changed_at = models.DateTimeField(auto_now_add=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    reason = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-changed_at"]

    def __str__(self):
        return f"{self.toy} {self.from_status}->{self.to_status}"


class IntakeRecord(TimeStampedModel):
    class IntakeType(models.TextChoices):
        DONATION = "DONATION", "Donation"
        POST_REPAIR = "POST_REPAIR", "Post-repair"
        INITIAL_PURCHASE = "INITIAL_PURCHASE", "Initial purchase"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    toy = models.ForeignKey(Toy, on_delete=models.CASCADE, related_name="intake_records")
    intake_type = models.CharField(max_length=20, choices=IntakeType.choices)
    assessed_condition = models.CharField(max_length=20, choices=Toy.Condition.choices)
    assessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    notes = models.TextField(blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Intake for {self.toy} ({self.intake_type})"
