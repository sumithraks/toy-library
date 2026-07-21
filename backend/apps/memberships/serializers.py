from rest_framework import serializers

from .models import Membership, MembershipSignOff, MembershipTier, MembershipTierChange


class MembershipTierSerializer(serializers.ModelSerializer):
    class Meta:
        model = MembershipTier
        fields = [
            "id",
            "code",
            "name",
            "joining_fee",
            "deposit_amount",
            "renewal_fee",
            "max_concurrent_checkouts",
            "loan_period_days",
            "complimentary_extension_days",
            "is_active",
        ]


class MembershipSignOffSerializer(serializers.ModelSerializer):
    class Meta:
        model = MembershipSignOff
        fields = [
            "id",
            "membership",
            "status",
            "requested_at",
            "requested_by",
            "approved_at",
            "approved_by",
            "rejection_reason",
            "processed_at",
            "processed_by",
            "deposit_amount_due",
            "deposit_amount_returned",
            "deduction_reason",
        ]
        read_only_fields = fields


class MembershipSerializer(serializers.ModelSerializer):
    tier = MembershipTierSerializer(read_only=True)
    sign_off = MembershipSignOffSerializer(read_only=True, allow_null=True)

    class Meta:
        model = Membership
        fields = [
            "id",
            "user",
            "tier",
            "status",
            "joined_at",
            "renewed_through",
            "discontinued_at",
            "sign_off",
        ]
        read_only_fields = fields


class MembershipSignupSerializer(serializers.Serializer):
    tier_code = serializers.ChoiceField(choices=MembershipTier.Code.choices)


class ChangeTierSerializer(serializers.Serializer):
    new_tier_code = serializers.ChoiceField(choices=MembershipTier.Code.choices)


class ApproveTerminationSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class RefundDepositSerializer(serializers.Serializer):
    amount_returned = serializers.DecimalField(max_digits=6, decimal_places=2)
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class MembershipTierChangeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MembershipTierChange
        fields = ["id", "membership", "from_tier", "to_tier", "changed_at", "changed_by"]
        read_only_fields = fields
