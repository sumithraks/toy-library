from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("staff", views.AdminUserViewSet, basename="staff-user")

urlpatterns = [
    path("signup/", views.SignupView.as_view(), name="signup"),
    path("verify-email/", views.VerifyEmailView.as_view(), name="verify-email"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("2fa/verify/", views.TwoFactorVerifyView.as_view(), name="2fa-verify"),
    path("2fa/enroll/", views.TwoFactorEnrollView.as_view(), name="2fa-enroll"),
    path("2fa/confirm/", views.TwoFactorConfirmView.as_view(), name="2fa-confirm"),
    path("2fa/disable/", views.TwoFactorDisableView.as_view(), name="2fa-disable"),
    path("password-change/", views.ChangePasswordView.as_view(), name="password-change"),
    path("password-reset/request/", views.PasswordResetRequestView.as_view(), name="password-reset-request"),
    path("password-reset/confirm/", views.PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("me/", views.MeView.as_view(), name="me"),
] + router.urls
