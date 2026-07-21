import uuid

from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class Reservation(TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        PICKED_UP = "PICKED_UP", "Picked up"
        EXPIRED = "EXPIRED", "Expired"
        CANCELLED = "CANCELLED", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    toy = models.ForeignKey("inventory.Toy", on_delete=models.CASCADE, related_name="reservations")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reservations"
    )
    reserved_at = models.DateTimeField(auto_now_add=True)
    pickup_by_date = models.DateField()
    pickup_deadline = models.DateTimeField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    picked_up_at = models.DateTimeField(null=True, blank=True)
    resulting_checkout = models.OneToOneField(
        "checkouts.CheckoutRecord", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    waitlist_entry = models.OneToOneField(
        "waitlist.WaitlistEntry", on_delete=models.SET_NULL, null=True, blank=True, related_name="reservation"
    )
    confirmation_sent_at = models.DateTimeField(null=True, blank=True)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-reserved_at"]
        indexes = [models.Index(fields=["status", "pickup_deadline"])]

    def __str__(self):
        return f"Reservation {self.toy} for {self.user} ({self.status})"
