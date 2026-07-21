from rest_framework import serializers

from .models import IntakeRecord, Toy, ToyStatusLog


class ToySerializer(serializers.ModelSerializer):
    class Meta:
        model = Toy
        fields = [
            "id",
            "model_name",
            "make",
            "min_age_years",
            "age_rating_label",
            "description",
            "status",
            "condition",
            "source",
            "donation",
            "image",
            "barcode_or_sku",
            "retired_at",
            "retired_reason",
            "created_at",
        ]
        read_only_fields = ["id", "status", "created_at"]


class ToyTransitionSerializer(serializers.Serializer):
    new_status = serializers.ChoiceField(choices=Toy.Status.choices)
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class ToyStatusLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ToyStatusLog
        fields = ["id", "toy", "from_status", "to_status", "changed_by", "reason", "changed_at"]
        read_only_fields = fields


class IntakeRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntakeRecord
        fields = [
            "id",
            "toy",
            "intake_type",
            "assessed_condition",
            "assessed_by",
            "notes",
            "completed_at",
        ]
        read_only_fields = ["id"]
