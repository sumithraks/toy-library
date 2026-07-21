from rest_framework import serializers

from .models import Reservation


class ReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reservation
        fields = [
            "id",
            "toy",
            "user",
            "reserved_at",
            "pickup_by_date",
            "pickup_deadline",
            "status",
            "picked_up_at",
            "resulting_checkout",
            "waitlist_entry",
        ]
        read_only_fields = [
            "id",
            "user",
            "reserved_at",
            "pickup_deadline",
            "status",
            "picked_up_at",
            "resulting_checkout",
            "waitlist_entry",
        ]


class CreateReservationSerializer(serializers.Serializer):
    toy = serializers.UUIDField()
    pickup_by_date = serializers.DateField()
