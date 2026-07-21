from django.contrib import admin

from .models import Membership, MembershipSignOff, MembershipTier, MembershipTierChange


@admin.register(MembershipTier)
class MembershipTierAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "code",
        "joining_fee",
        "deposit_amount",
        "renewal_fee",
        "max_concurrent_checkouts",
        "loan_period_days",
        "complimentary_extension_days",
        "is_active",
    ]


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ["user", "tier", "status", "joined_at", "renewed_through"]
    list_filter = ["status", "tier"]
    search_fields = ["user__email"]


@admin.register(MembershipTierChange)
class MembershipTierChangeAdmin(admin.ModelAdmin):
    list_display = ["membership", "from_tier", "to_tier", "changed_at", "changed_by"]


@admin.register(MembershipSignOff)
class MembershipSignOffAdmin(admin.ModelAdmin):
    list_display = ["membership", "deposit_amount_due", "deposit_amount_returned", "processed_at"]
