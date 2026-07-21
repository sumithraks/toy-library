import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.common.models import TimeStampedModel


class WaitlistEntry(TimeStampedModel):
    class Status(models.TextChoices):
        WAITING = "WAITING", "Waiting"
        CONVERTED_TO_RESERVATION = "CONVERTED_TO_RESERVATION", "Converted to reservation"
        EXPIRED = "EXPIRED", "Expired"
        CANCELLED = "CANCELLED", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    toy = models.ForeignKey("inventory.Toy", on_delete=models.CASCADE, related_name="waitlist_entries")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="waitlist_entries"
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.WAITING)
    converted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["joined_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["toy", "user"],
                condition=Q(status="WAITING"),
                name="unique_active_waitlist_entry",
            )
        ]

    def __str__(self):
        return f"{self.user} waiting for {self.toy} ({self.status})"
