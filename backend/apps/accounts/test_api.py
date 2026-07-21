import pytest
from django.core import mail
from django_otp.oath import totp
from rest_framework.test import APIClient

from apps.common.factories import UserFactory

from .models import SingleUseToken


def _totp_code(device, step_offset=0):
    # django_otp's TOTPDevice rejects reusing the same time-step counter twice
    # (anti-replay). step_offset lets a test mint a code for a later window
    # without sleeping 30s in real time.
    return str(totp(device.bin_key, t0=-step_offset * 30)).zfill(6)


@pytest.mark.django_db
class TestSignup:
    def test_signup_creates_unverified_user_and_sends_email(self, api_client):
        res = api_client.post(
            "/api/auth/signup/",
            {"email": "new@example.com", "password": "testpass123", "first_name": "New"},
        )

        assert res.status_code == 201
        assert res.data["email"] == "new@example.com"
        assert res.data["is_email_verified"] is False
        assert len(mail.outbox) == 1
        assert "verify" in mail.outbox[0].subject.lower()

    def test_signup_rejects_duplicate_email(self, api_client):
        UserFactory(email="dupe@example.com")

        res = api_client.post(
            "/api/auth/signup/", {"email": "dupe@example.com", "password": "testpass123"}
        )

        assert res.status_code == 400

    def test_signup_rejects_short_password(self, api_client):
        res = api_client.post(
            "/api/auth/signup/", {"email": "short@example.com", "password": "abc"}
        )

        assert res.status_code == 400


@pytest.mark.django_db
class TestVerifyEmail:
    def test_verify_email_with_valid_token(self, api_client):
        signup_res = api_client.post(
            "/api/auth/signup/", {"email": "verify@example.com", "password": "testpass123"}
        )
        token = SingleUseToken.objects.get(
            user__email="verify@example.com", purpose=SingleUseToken.Purpose.EMAIL_VERIFICATION
        )

        res = api_client.post("/api/auth/verify-email/", {"token": str(token.token)})

        assert res.status_code == 200
        assert res.data["is_email_verified"] is True

    def test_verify_email_with_invalid_token(self, api_client):
        res = api_client.post(
            "/api/auth/verify-email/", {"token": "00000000-0000-0000-0000-000000000000"}
        )

        assert res.status_code == 400

    def test_verify_email_token_cannot_be_reused(self, api_client):
        api_client.post(
            "/api/auth/signup/", {"email": "reuse@example.com", "password": "testpass123"}
        )
        token = SingleUseToken.objects.get(
            user__email="reuse@example.com", purpose=SingleUseToken.Purpose.EMAIL_VERIFICATION
        )
        api_client.post("/api/auth/verify-email/", {"token": str(token.token)})

        res = api_client.post("/api/auth/verify-email/", {"token": str(token.token)})

        assert res.status_code == 400


@pytest.mark.django_db
class TestLogin:
    def test_login_without_2fa_returns_token(self, api_client):
        UserFactory(email="login@example.com", password="testpass123")

        res = api_client.post(
            "/api/auth/login/", {"email": "login@example.com", "password": "testpass123"}
        )

        assert res.status_code == 200
        assert res.data["requires_2fa"] is False
        assert "token" in res.data

    def test_login_with_wrong_password_is_rejected(self, api_client):
        UserFactory(email="wrongpw@example.com", password="testpass123")

        res = api_client.post(
            "/api/auth/login/", {"email": "wrongpw@example.com", "password": "nope"}
        )

        assert res.status_code == 401

    def test_login_with_confirmed_totp_returns_pre_auth_token(self, api_client):
        user = UserFactory(email="twofactor@example.com", password="testpass123")
        api_client.force_authenticate(user=user)
        api_client.post("/api/auth/2fa/enroll/")
        from django_otp.plugins.otp_totp.models import TOTPDevice

        device = TOTPDevice.objects.get(user=user, confirmed=False)
        api_client.post("/api/auth/2fa/confirm/", {"code": _totp_code(device)})
        api_client.force_authenticate(user=None)

        res = api_client.post(
            "/api/auth/login/", {"email": "twofactor@example.com", "password": "testpass123"}
        )

        assert res.status_code == 200
        assert res.data["requires_2fa"] is True
        assert "pre_auth_token" in res.data
        assert "token" not in res.data


@pytest.mark.django_db
class TestTwoFactorFlow:
    def test_enroll_confirm_verify_full_cycle(self, member_client, member):
        enroll_res = member_client.post("/api/auth/2fa/enroll/")
        assert enroll_res.status_code == 200
        assert "otpauth_uri" in enroll_res.data

        from django_otp.plugins.otp_totp.models import TOTPDevice

        device = TOTPDevice.objects.get(user=member, confirmed=False)
        confirm_res = member_client.post("/api/auth/2fa/confirm/", {"code": _totp_code(device)})

        assert confirm_res.status_code == 200
        assert len(confirm_res.data["recovery_codes"]) == 10

        device.refresh_from_db()
        assert device.confirmed is True

        login_res = member_client.post(
            "/api/auth/login/", {"email": member.email, "password": "testpass123"}
        )
        pre_auth_token = login_res.data["pre_auth_token"]

        verify_res = member_client.post(
            "/api/auth/2fa/verify/",
            {"pre_auth_token": pre_auth_token, "code": _totp_code(device, step_offset=1)},
        )
        assert verify_res.status_code == 200
        assert "token" in verify_res.data

    def test_verify_rejects_invalid_code(self, member_client, member):
        member_client.post("/api/auth/2fa/enroll/")
        from django_otp.plugins.otp_totp.models import TOTPDevice

        device = TOTPDevice.objects.get(user=member, confirmed=False)
        member_client.post("/api/auth/2fa/confirm/", {"code": _totp_code(device)})
        login_res = member_client.post(
            "/api/auth/login/", {"email": member.email, "password": "testpass123"}
        )

        res = member_client.post(
            "/api/auth/2fa/verify/",
            {"pre_auth_token": login_res.data["pre_auth_token"], "code": "000000"},
        )

        assert res.status_code == 400

    def test_disable_removes_device(self, member_client, member):
        member_client.post("/api/auth/2fa/enroll/")
        from django_otp.plugins.otp_totp.models import TOTPDevice

        device = TOTPDevice.objects.get(user=member, confirmed=False)
        member_client.post("/api/auth/2fa/confirm/", {"code": _totp_code(device)})

        res = member_client.post("/api/auth/2fa/disable/")

        assert res.status_code == 204
        assert not TOTPDevice.objects.filter(user=member).exists()

    def test_enroll_requires_authentication(self, api_client):
        res = api_client.post("/api/auth/2fa/enroll/")
        assert res.status_code == 401


@pytest.mark.django_db
class TestMe:
    def test_get_me_requires_authentication(self, api_client):
        res = api_client.get("/api/auth/me/")
        assert res.status_code == 401

    def test_get_me_returns_current_user(self, member_client, member):
        res = member_client.get("/api/auth/me/")

        assert res.status_code == 200
        assert res.data["email"] == member.email

    def test_patch_me_updates_profile_fields(self, member_client):
        res = member_client.patch("/api/auth/me/", {"first_name": "Updated"})

        assert res.status_code == 200
        assert res.data["first_name"] == "Updated"

    def test_patch_me_cannot_change_email_or_staff_flag(self, member_client, member):
        original_email = member.email
        res = member_client.patch(
            "/api/auth/me/", {"email": "hacker@example.com", "is_staff": True}
        )

        assert res.status_code == 200
        member.refresh_from_db()
        assert member.email == original_email
        assert member.is_staff is False


@pytest.mark.django_db
class TestChangePassword:
    def test_requires_authentication(self, api_client):
        res = api_client.post(
            "/api/auth/password-change/",
            {"current_password": "testpass123", "new_password": "newpass456"},
        )
        assert res.status_code == 401

    def test_wrong_current_password_fails(self, member_client):
        res = member_client.post(
            "/api/auth/password-change/",
            {"current_password": "wrongpass", "new_password": "newpass456"},
        )
        assert res.status_code == 400

    def test_new_password_too_short_fails(self, member_client):
        res = member_client.post(
            "/api/auth/password-change/",
            {"current_password": "testpass123", "new_password": "short"},
        )
        assert res.status_code == 400

    def test_correct_current_password_changes_password(self, member_client, member):
        res = member_client.post(
            "/api/auth/password-change/",
            {"current_password": "testpass123", "new_password": "newpass456"},
        )

        assert res.status_code == 200
        login_res = APIClient().post(
            "/api/auth/login/", {"email": member.email, "password": "newpass456"}
        )
        assert login_res.status_code == 200


@pytest.mark.django_db
class TestPasswordReset:
    def test_request_for_existing_user_sends_email(self, api_client, member):
        res = api_client.post("/api/auth/password-reset/request/", {"email": member.email})

        assert res.status_code == 200
        assert len(mail.outbox) == 1

    def test_request_for_unknown_email_still_returns_200(self, api_client):
        res = api_client.post(
            "/api/auth/password-reset/request/", {"email": "nobody@example.com"}
        )

        assert res.status_code == 200
        assert len(mail.outbox) == 0

    def test_confirm_with_valid_token_changes_password(self, api_client, member):
        api_client.post("/api/auth/password-reset/request/", {"email": member.email})
        token = SingleUseToken.objects.get(
            user=member, purpose=SingleUseToken.Purpose.PASSWORD_RESET
        )

        res = api_client.post(
            "/api/auth/password-reset/confirm/",
            {"token": str(token.token), "password": "newpass456"},
        )

        assert res.status_code == 200
        login_res = api_client.post(
            "/api/auth/login/", {"email": member.email, "password": "newpass456"}
        )
        assert login_res.status_code == 200

    def test_confirm_with_invalid_token_fails(self, api_client):
        res = api_client.post(
            "/api/auth/password-reset/confirm/",
            {"token": "00000000-0000-0000-0000-000000000000", "password": "whatever123"},
        )

        assert res.status_code == 400


@pytest.mark.django_db
class TestAdminUserManagement:
    def test_requires_admin_to_list(self, member_client, staff_client, admin_client):
        assert member_client.get("/api/auth/staff/").status_code == 403
        assert staff_client.get("/api/auth/staff/").status_code == 403
        assert admin_client.get("/api/auth/staff/").status_code == 200

    def test_admin_creates_staff_user(self, admin_client):
        res = admin_client.post(
            "/api/auth/staff/",
            {
                "email": "brandnew@example.com",
                "password": "startpass123",
                "first_name": "Brand",
                "last_name": "New",
            },
        )

        assert res.status_code == 201
        assert res.data["role"] == "STAFF"

        login_res = admin_client.post(
            "/api/auth/login/", {"email": "brandnew@example.com", "password": "startpass123"}
        )
        assert login_res.status_code == 200

    def test_admin_creates_staff_user_requires_password(self, admin_client):
        res = admin_client.post("/api/auth/staff/", {"email": "nopassword@example.com"})
        assert res.status_code == 400

    def test_staff_cannot_create_staff_user(self, staff_client):
        res = staff_client.post(
            "/api/auth/staff/", {"email": "nope@example.com", "password": "startpass123"}
        )
        assert res.status_code == 403

    def test_admin_deactivates_and_reactivates_staff(self, admin_client, staff_user):
        deactivate_res = admin_client.post(f"/api/auth/staff/{staff_user.id}/deactivate/")
        assert deactivate_res.status_code == 200
        assert deactivate_res.data["is_active"] is False

        reactivate_res = admin_client.post(f"/api/auth/staff/{staff_user.id}/reactivate/")
        assert reactivate_res.status_code == 200
        assert reactivate_res.data["is_active"] is True

    def test_admin_promotes_staff_to_admin(self, admin_client, staff_user):
        res = admin_client.post(f"/api/auth/staff/{staff_user.id}/set-role/", {"role": "ADMIN"})

        assert res.status_code == 200
        assert res.data["role"] == "ADMIN"

    def test_admin_cannot_change_role_of_deactivated_staff(self, admin_client, staff_user):
        admin_client.post(f"/api/auth/staff/{staff_user.id}/deactivate/")

        res = admin_client.post(f"/api/auth/staff/{staff_user.id}/set-role/", {"role": "ADMIN"})

        assert res.status_code == 400

    def test_admin_cannot_change_own_role(self, admin_client, admin_user):
        res = admin_client.post(f"/api/auth/staff/{admin_user.id}/set-role/", {"role": "STAFF"})
        assert res.status_code == 400
