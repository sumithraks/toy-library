from rest_framework import serializers

from .models import User


class SignupSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(required=False, allow_blank=True, default="")
    last_name = serializers.CharField(required=False, allow_blank=True, default="")
    phone_number = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value


class VerifyEmailSerializer(serializers.Serializer):
    token = serializers.UUIDField()


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class TwoFactorVerifySerializer(serializers.Serializer):
    pre_auth_token = serializers.UUIDField()
    code = serializers.CharField()


class TwoFactorConfirmSerializer(serializers.Serializer):
    code = serializers.CharField()


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "is_email_verified",
            "is_staff",
            "role",
            "is_active",
            "date_joined",
        ]
        read_only_fields = [
            "id",
            "email",
            "is_email_verified",
            "is_staff",
            "role",
            "is_active",
            "date_joined",
        ]


class CreateStaffSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(required=False, allow_blank=True, default="")
    last_name = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value


class SetRoleSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=[User.Role.STAFF, User.Role.ADMIN])
