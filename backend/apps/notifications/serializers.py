from rest_framework import serializers

from .models import NotificationLog, NotificationPreference, PushSubscription


class NotificationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationLog
        fields = ["id", "event_type", "channel", "title", "body", "action_url", "sent_at", "read_at"]
        read_only_fields = fields


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = [
            "email_enabled",
            "push_enabled",
            "due_date_reminders",
            "waitlist_alerts",
            "reservation_alerts",
            "billing_alerts",
        ]


class PushSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PushSubscription
        fields = ["id", "endpoint", "p256dh_key", "auth_key", "user_agent"]
        read_only_fields = ["id"]
