from django.contrib import admin

from .models import Donation, DonationItem, DonationReceipt, Donor


class DonationItemInline(admin.TabularInline):
    model = DonationItem
    extra = 0


@admin.register(Donor)
class DonorAdmin(admin.ModelAdmin):
    list_display = ["name", "email", "phone", "user"]
    search_fields = ["name", "email"]


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ["id", "donor", "status", "donated_at"]
    list_filter = ["status"]
    inlines = [DonationItemInline]


@admin.register(DonationReceipt)
class DonationReceiptAdmin(admin.ModelAdmin):
    list_display = ["receipt_number", "donation", "issued_at"]
