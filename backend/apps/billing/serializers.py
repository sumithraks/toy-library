from rest_framework import serializers

from .models import LedgerEntry


class LedgerEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = LedgerEntry
        fields = [
            "id",
            "user",
            "entry_type",
            "amount",
            "direction",
            "status",
            "due_date",
            "paid_at",
            "marked_paid_by",
            "notes",
            "related_checkout",
            "related_membership",
            "related_donation",
            "created_at",
        ]
        read_only_fields = fields
