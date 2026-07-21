from django.contrib import admin

from .models import WaitlistEntry


@admin.register(WaitlistEntry)
class WaitlistEntryAdmin(admin.ModelAdmin):
    list_display = ["toy", "user", "status", "joined_at", "converted_at"]
    list_filter = ["status"]
