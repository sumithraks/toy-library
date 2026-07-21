from django.contrib import admin

from .models import CheckoutRecord, Extension, LateFeeAssessment


@admin.register(CheckoutRecord)
class CheckoutRecordAdmin(admin.ModelAdmin):
    list_display = ["toy", "member", "status", "checked_out_at", "current_due_date"]
    list_filter = ["status"]
    search_fields = ["toy__model_name", "member__email"]


@admin.register(Extension)
class ExtensionAdmin(admin.ModelAdmin):
    list_display = ["checkout", "extension_type", "days_added", "previous_due_date", "new_due_date", "applied"]
    list_filter = ["extension_type", "applied"]


@admin.register(LateFeeAssessment)
class LateFeeAssessmentAdmin(admin.ModelAdmin):
    list_display = ["checkout", "assessed_at", "days_late_at_assessment", "fee_amount"]
