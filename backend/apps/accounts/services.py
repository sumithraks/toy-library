import hashlib
import secrets

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django_otp.plugins.otp_totp.models import TOTPDevice

from apps.notifications.services import notify

from .models import PreAuthToken, SingleUseToken, TwoFactorRecoveryCode, User


def signup(email, password, first_name="", last_name="", phone_number=""):
    with transaction.atomic():
        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
        )
        issue_email_verification_token(user)
    return user


def issue_email_verification_token(user):
    return SingleUseToken.objects.create(
        user=user,
        purpose=SingleUseToken.Purpose.EMAIL_VERIFICATION,
        expires_at=timezone.now()
        + timezone.timedelta(hours=settings.EMAIL_VERIFICATION_TOKEN_TTL_HOURS),
    )


def verify_email(token_value):
    try:
        token = SingleUseToken.objects.get(
            token=token_value, purpose=SingleUseToken.Purpose.EMAIL_VERIFICATION
        )
    except SingleUseToken.DoesNotExist:
        raise ValueError("Invalid verification token")
    if not token.is_valid():
        raise ValueError("Verification token expired or already used")
    with transaction.atomic():
        token.used_at = timezone.now()
        token.save(update_fields=["used_at"])
        user = token.user
        user.is_email_verified = True
        user.save(update_fields=["is_email_verified"])
    return user


def issue_pre_auth_token(user):
    return PreAuthToken.objects.create(
        user=user,
        expires_at=timezone.now()
        + timezone.timedelta(minutes=settings.PRE_AUTH_TOKEN_TTL_MINUTES),
    )


def user_has_confirmed_totp(user):
    return TOTPDevice.objects.filter(user=user, confirmed=True).exists()


def enroll_totp(user):
    TOTPDevice.objects.filter(user=user, confirmed=False).delete()
    device = TOTPDevice.objects.create(user=user, name="default", confirmed=False)
    return device


def confirm_totp(user, token_code):
    device = TOTPDevice.objects.filter(user=user, confirmed=False).order_by("-id").first()
    if device is None or not device.verify_token(token_code):
        raise ValueError("Invalid or expired code")
    device.confirmed = True
    device.save(update_fields=["confirmed"])
    return generate_recovery_codes(user)


def disable_totp(user):
    TOTPDevice.objects.filter(user=user).delete()
    TwoFactorRecoveryCode.objects.filter(user=user).delete()


def verify_totp_or_recovery_code(user, code):
    device = TOTPDevice.objects.filter(user=user, confirmed=True).first()
    if device and device.verify_token(code):
        return True
    code_hash = hashlib.sha256(code.encode()).hexdigest()
    recovery = TwoFactorRecoveryCode.objects.filter(
        user=user, code_hash=code_hash, used_at__isnull=True
    ).first()
    if recovery:
        recovery.used_at = timezone.now()
        recovery.save(update_fields=["used_at"])
        return True
    return False


def change_password(user, current_password, new_password):
    if not user.check_password(current_password):
        raise ValueError("Current password is incorrect")
    user.set_password(new_password)
    user.save(update_fields=["password"])


def create_staff_user(email, first_name="", last_name=""):
    with transaction.atomic():
        user = User.objects.create_user(
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=User.Role.STAFF,
            is_staff=True,
            is_email_verified=True,
        )
        user.set_unusable_password()
        user.save(update_fields=["password"])
        token = SingleUseToken.objects.create(
            user=user,
            purpose=SingleUseToken.Purpose.PASSWORD_RESET,
            expires_at=timezone.now() + timezone.timedelta(hours=2),
        )

    notify(
        user,
        event_type="PASSWORD_RESET",
        title="Set your Toy Library staff password",
        body="An admin has created a staff account for you. Use the link to set your password.",
        action_url=f"/password-reset/confirm?token={token.token}",
    )
    return user


def set_staff_role(target_user, new_role, actor):
    if new_role not in (User.Role.STAFF, User.Role.ADMIN):
        raise ValueError("role must be STAFF or ADMIN")
    if target_user.role not in (User.Role.STAFF, User.Role.ADMIN):
        raise ValueError("Only STAFF or ADMIN accounts can have their role changed")
    if target_user.pk == actor.pk:
        raise ValueError("You cannot change your own role")
    target_user.role = new_role
    target_user.is_staff = True
    target_user.save(update_fields=["role", "is_staff"])
    return target_user


def deactivate_staff_user(target_user):
    if target_user.role not in (User.Role.STAFF, User.Role.ADMIN):
        raise ValueError("Only STAFF or ADMIN accounts can be deactivated here")
    target_user.is_active = False
    target_user.save(update_fields=["is_active"])
    return target_user


def reactivate_staff_user(target_user):
    if target_user.role not in (User.Role.STAFF, User.Role.ADMIN):
        raise ValueError("Only STAFF or ADMIN accounts can be reactivated here")
    target_user.is_active = True
    target_user.save(update_fields=["is_active"])
    return target_user


def generate_recovery_codes(user, count=10):
    TwoFactorRecoveryCode.objects.filter(user=user, used_at__isnull=True).delete()
    plain_codes = []
    for _ in range(count):
        code = secrets.token_hex(4)
        plain_codes.append(code)
        TwoFactorRecoveryCode.objects.create(
            user=user, code_hash=hashlib.sha256(code.encode()).hexdigest()
        )
    return plain_codes
