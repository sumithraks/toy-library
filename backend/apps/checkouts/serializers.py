from rest_framework import serializers

from .models import CheckoutRecord, Extension


class ExtensionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Extension
        fields = [
            "id",
            "checkout",
            "extension_type",
            "requested_at",
            "days_added",
            "previous_due_date",
            "new_due_date",
            "ledger_entry",
            "applied",
        ]
        read_only_fields = fields


class CheckoutRecordSerializer(serializers.ModelSerializer):
    complimentary_extension_available = serializers.SerializerMethodField()
    paid_extension_rate = serializers.SerializerMethodField()

    class Meta:
        model = CheckoutRecord
        fields = [
            "id",
            "toy",
            "member",
            "membership",
            "checked_out_at",
            "checked_out_by",
            "original_due_date",
            "current_due_date",
            "complimentary_extension_used",
            "complimentary_extension_available",
            "paid_extension_rate",
            "status",
            "returned_at",
            "returned_to",
            "return_condition",
        ]
        read_only_fields = fields

    def get_complimentary_extension_available(self, obj):
        return obj.status == CheckoutRecord.Status.ACTIVE and not obj.complimentary_extension_used

    def get_paid_extension_rate(self, obj):
        return "0.05"


class CreateCheckoutSerializer(serializers.Serializer):
    toy = serializers.UUIDField()
    member = serializers.UUIDField()


class ReturnCheckoutSerializer(serializers.Serializer):
    condition = serializers.ChoiceField(
        choices=[("NEW", "New"), ("LIGHTLY_USED", "Lightly used"), ("USED", "Used"), ("DAMAGED", "Damaged")]
    )
    damaged_status = serializers.ChoiceField(
        choices=[("UNDER_REPAIR", "Under repair"), ("BROKEN", "Broken")], required=False, allow_null=True
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class ComplimentaryExtensionSerializer(serializers.Serializer):
    pass


class PaidExtensionSerializer(serializers.Serializer):
    days = serializers.IntegerField(min_value=1, max_value=30)
