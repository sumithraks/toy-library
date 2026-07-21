from django.contrib import admin

from .models import LedgerEntry


@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = ["user", "entry_type", "direction", "amount", "status", "due_date", "created_at"]
    list_filter = ["entry_type", "direction", "status"]
    search_fields = ["user__email", "notes"]
    readonly_fields = ["created_at", "updated_at"]
