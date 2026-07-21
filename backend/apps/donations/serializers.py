from rest_framework import serializers

from .models import Donation, DonationItem, DonationReceipt, Donor


class DonorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Donor
        fields = ["id", "user", "name", "email", "phone"]
        read_only_fields = ["id"]


class DonationItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = DonationItem
        fields = [
            "id",
            "donation",
            "item_type",
            "description",
            "make",
            "model_name",
            "age_rating",
            "toy",
        ]
        read_only_fields = ["id", "donation", "toy"]


class DonationItemCreateSerializer(serializers.Serializer):
    item_type = serializers.ChoiceField(choices=DonationItem.ItemType.choices)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    make = serializers.CharField(required=False, allow_blank=True, default="")
    model_name = serializers.CharField(required=False, allow_blank=True, default="")
    age_rating = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_item_type(self, value):
        if value in DonationItem.DISALLOWED_TYPES:
            raise serializers.ValidationError(
                "Soft toys and dolls are not accepted as donations."
            )
        return value


class DonorCreateSerializer(serializers.Serializer):
    name = serializers.CharField()
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    phone = serializers.CharField(required=False, allow_blank=True, default="")


class DonationSubmitSerializer(serializers.Serializer):
    donor = DonorCreateSerializer()
    items = DonationItemCreateSerializer(many=True)


class DonationSerializer(serializers.ModelSerializer):
    donor = DonorSerializer(read_only=True)
    items = DonationItemSerializer(many=True, read_only=True)

    class Meta:
        model = Donation
        fields = ["id", "donor", "donated_at", "status", "rejection_reason", "items"]
        read_only_fields = fields


class DonationRejectSerializer(serializers.Serializer):
    reason = serializers.CharField()


class CompleteIntakeSerializer(serializers.Serializer):
    condition = serializers.ChoiceField(choices=[("NEW", "New"), ("LIGHTLY_USED", "Lightly used"), ("USED", "Used"), ("DAMAGED", "Damaged")])
    age_rating = serializers.CharField(required=False, allow_blank=True, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class DonationReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = DonationReceipt
        fields = ["id", "donation", "receipt_number", "issued_at", "pdf_file", "summary_text"]
        read_only_fields = fields
