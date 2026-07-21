import base64
import io

import qrcode
from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework import generics, mixins, permissions, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsAdmin
from apps.notifications.services import notify

from . import services
from .models import PreAuthToken, SingleUseToken, User
from .serializers import (
    ChangePasswordSerializer,
    CreateStaffSerializer,
    LoginSerializer,
    SetRoleSerializer,
    SignupSerializer,
    TwoFactorConfirmSerializer,
    TwoFactorVerifySerializer,
    UserSerializer,
    VerifyEmailSerializer,
)


class SignupView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = services.signup(**serializer.validated_data)
        token = SingleUseToken.objects.filter(
            user=user, purpose=SingleUseToken.Purpose.EMAIL_VERIFICATION
        ).latest("created_at")
        notify(
            user,
            event_type="EMAIL_VERIFICATION",
            title="Verify your Toy Library email",
            body="Please verify your email to activate your account.",
            action_url=f"/verify-email?token={token.token}",
        )
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class VerifyEmailView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = services.verify_email(serializer.validated_data["token"])
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(UserSerializer(user).data)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            username=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )
        if user is None:
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        if services.user_has_confirmed_totp(user):
            pre_auth = services.issue_pre_auth_token(user)
            return Response({"pre_auth_token": str(pre_auth.id), "requires_2fa": True})

        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "requires_2fa": False})


class TwoFactorVerifyView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = TwoFactorVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            pre_auth = PreAuthToken.objects.get(id=serializer.validated_data["pre_auth_token"])
        except PreAuthToken.DoesNotExist:
            return Response({"detail": "Invalid pre-auth token"}, status=status.HTTP_400_BAD_REQUEST)
        if not pre_auth.is_valid():
            return Response({"detail": "Pre-auth token expired"}, status=status.HTTP_400_BAD_REQUEST)
        if not services.verify_totp_or_recovery_code(pre_auth.user, serializer.validated_data["code"]):
            return Response({"detail": "Invalid code"}, status=status.HTTP_400_BAD_REQUEST)

        pre_auth.used_at = timezone.now()
        pre_auth.save(update_fields=["used_at"])
        token, _ = Token.objects.get_or_create(user=pre_auth.user)
        return Response({"token": token.key})


class TwoFactorEnrollView(APIView):
    def post(self, request):
        device = services.enroll_totp(request.user)
        qr_img = qrcode.make(device.config_url)
        buf = io.BytesIO()
        qr_img.save(buf, format="PNG")
        qr_b64 = base64.b64encode(buf.getvalue()).decode()
        return Response({"otpauth_uri": device.config_url, "qr_code_png_base64": qr_b64})


class TwoFactorConfirmView(APIView):
    def post(self, request):
        serializer = TwoFactorConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            recovery_codes = services.confirm_totp(request.user, serializer.validated_data["code"])
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"recovery_codes": recovery_codes})


class TwoFactorDisableView(APIView):
    def post(self, request):
        services.disable_totp(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            services.change_password(
                request.user,
                serializer.validated_data["current_password"],
                serializer.validated_data["new_password"],
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_200_OK)


class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email", "")
        user = User.objects.filter(email__iexact=email).first()
        if user is not None:
            token = SingleUseToken.objects.create(
                user=user,
                purpose=SingleUseToken.Purpose.PASSWORD_RESET,
                expires_at=timezone.now() + timezone.timedelta(hours=2),
            )
            notify(
                user,
                event_type="PASSWORD_RESET",
                title="Reset your Toy Library password",
                body="Use the link to reset your password.",
                action_url=f"/password-reset/confirm?token={token.token}",
            )
        # Always 200 regardless of whether the email exists, to avoid account enumeration.
        return Response(status=status.HTTP_200_OK)


class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        token_value = request.data.get("token")
        new_password = request.data.get("password")
        try:
            token = SingleUseToken.objects.get(
                token=token_value, purpose=SingleUseToken.Purpose.PASSWORD_RESET
            )
        except SingleUseToken.DoesNotExist:
            return Response({"detail": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)
        if not token.is_valid():
            return Response({"detail": "Token expired or already used"}, status=status.HTTP_400_BAD_REQUEST)
        user = token.user
        user.set_password(new_password)
        user.save(update_fields=["password"])
        token.used_at = timezone.now()
        token.save(update_fields=["used_at"])
        return Response(status=status.HTTP_200_OK)


class AdminUserViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAdmin]
    serializer_class = UserSerializer
    queryset = User.objects.filter(role__in=[User.Role.STAFF, User.Role.ADMIN]).order_by("-date_joined")

    def create(self, request, *args, **kwargs):
        serializer = CreateStaffSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = services.create_staff_user(**serializer.validated_data)
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        target_user = self.get_object()
        try:
            services.deactivate_staff_user(target_user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(UserSerializer(target_user).data)

    @action(detail=True, methods=["post"])
    def reactivate(self, request, pk=None):
        target_user = self.get_object()
        try:
            services.reactivate_staff_user(target_user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(UserSerializer(target_user).data)

    @action(detail=True, methods=["post"], url_path="set-role")
    def set_role(self, request, pk=None):
        target_user = self.get_object()
        serializer = SetRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            services.set_staff_role(target_user, serializer.validated_data["role"], request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(UserSerializer(target_user).data)
