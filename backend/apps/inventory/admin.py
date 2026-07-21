from django.contrib import admin

from .models import IntakeRecord, Toy, ToyStatusLog


@admin.register(Toy)
class ToyAdmin(admin.ModelAdmin):
    list_display = ["model_name", "make", "status", "condition", "source", "min_age_years"]
    list_filter = ["status", "condition", "source"]
    search_fields = ["model_name", "make", "barcode_or_sku"]


@admin.register(ToyStatusLog)
class ToyStatusLogAdmin(admin.ModelAdmin):
    list_display = ["toy", "from_status", "to_status", "changed_by", "changed_at"]
    list_filter = ["to_status"]


@admin.register(IntakeRecord)
class IntakeRecordAdmin(admin.ModelAdmin):
    list_display = ["toy", "intake_type", "assessed_condition", "assessed_by", "completed_at"]
    list_filter = ["intake_type"]
