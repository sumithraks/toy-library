from django.contrib import admin

from .models import NotificationLog, NotificationPreference, PushSubscription


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ["user", "email_enabled", "push_enabled"]


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ["user", "is_active", "last_seen_at"]
    list_filter = ["is_active"]


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ["user", "event_type", "channel", "sent_at", "read_at"]
    list_filter = ["channel", "event_type"]
