from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import PreAuthToken, SingleUseToken, TwoFactorRecoveryCode, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ["-date_joined"]
    list_display = ["email", "first_name", "last_name", "is_email_verified", "is_staff", "is_active"]
    list_filter = ["is_staff", "is_active", "is_email_verified"]
    search_fields = ["email", "first_name", "last_name"]
    readonly_fields = ["date_joined", "last_login"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "phone_number")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "is_email_verified",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2"),
            },
        ),
    )


@admin.register(SingleUseToken)
class SingleUseTokenAdmin(admin.ModelAdmin):
    list_display = ["user", "purpose", "expires_at", "used_at"]
    list_filter = ["purpose"]
    search_fields = ["user__email"]


@admin.register(TwoFactorRecoveryCode)
class TwoFactorRecoveryCodeAdmin(admin.ModelAdmin):
    list_display = ["user", "used_at", "created_at"]


@admin.register(PreAuthToken)
class PreAuthTokenAdmin(admin.ModelAdmin):
    list_display = ["user", "expires_at", "used_at"]
