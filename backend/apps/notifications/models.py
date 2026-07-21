import uuid

from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class NotificationPreference(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_preference"
    )
    email_enabled = models.BooleanField(default=True)
    push_enabled = models.BooleanField(default=True)
    due_date_reminders = models.BooleanField(default=True)
    waitlist_alerts = models.BooleanField(default=True)
    reservation_alerts = models.BooleanField(default=True)
    billing_alerts = models.BooleanField(default=True)

    def __str__(self):
        return f"Notification preferences for {self.user}"


CATEGORY_BY_EVENT_TYPE = {
    "DUE_DATE_REMINDER": "due_date_reminders",
    "EXTENSION_AVAILABLE": "due_date_reminders",
    "WAITLIST_AVAILABLE": "waitlist_alerts",
    "RESERVATION_CONFIRMED": "reservation_alerts",
    "RESERVATION_REMINDER": "reservation_alerts",
    "RESERVATION_EXPIRED": "reservation_alerts",
    "LATE_FEE_ASSESSED": "billing_alerts",
    "MEMBERSHIP_RENEWAL_DUE": "billing_alerts",
    "EMAIL_VERIFICATION": None,
    "PASSWORD_RESET": None,
}


class PushSubscription(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="push_subscriptions"
    )
    endpoint = models.URLField(max_length=500, unique=True)
    p256dh_key = models.CharField(max_length=255)
    auth_key = models.CharField(max_length=255)
    user_agent = models.CharField(max_length=255, blank=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Push subscription for {self.user}"


class NotificationLog(TimeStampedModel):
    class Channel(models.TextChoices):
        EMAIL = "EMAIL", "Email"
        PUSH = "PUSH", "Push"
        IN_APP = "IN_APP", "In-app"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_logs"
    )
    event_type = models.CharField(max_length=64)
    channel = models.CharField(max_length=16, choices=Channel.choices)
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)
    action_url = models.CharField(max_length=500, blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-sent_at"]
        indexes = [models.Index(fields=["user", "read_at"])]

    def __str__(self):
        return f"{self.event_type} ({self.channel}) to {self.user}"
