from rest_framework import serializers

from .models import WaitlistEntry


class WaitlistEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = WaitlistEntry
        fields = ["id", "toy", "user", "joined_at", "status", "converted_at"]
        read_only_fields = ["id", "user", "joined_at", "status", "converted_at"]


class JoinWaitlistSerializer(serializers.Serializer):
    toy = serializers.UUIDField()
