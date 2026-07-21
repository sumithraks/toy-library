from django.contrib import admin

from .models import Reservation


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ["toy", "user", "status", "pickup_by_date", "pickup_deadline"]
    list_filter = ["status"]
