from unittest.mock import Mock, patch

import pytest
from pywebpush import WebPushException

from apps.common.factories import UserFactory

from . import services
from .models import NotificationLog, PushSubscription


@pytest.mark.django_db
class TestNotify:
    def test_logs_push_channel_when_push_send_succeeds(self, settings):
        settings.VAPID_PRIVATE_KEY = "test-private-key"
        user = UserFactory()
        PushSubscription.objects.create(
            user=user, endpoint="https://push.example.com/x", p256dh_key="k", auth_key="a"
        )

        with patch("apps.notifications.services.webpush") as mock_webpush:
            mock_webpush.return_value = None
            services.notify(user, event_type="DUE_DATE_REMINDER", title="Hi", body="Body")

        assert NotificationLog.objects.filter(user=user, channel=NotificationLog.Channel.PUSH).exists()


@pytest.mark.django_db
class TestSendEmail:
    def test_noop_when_user_has_no_email(self):
        user = UserFactory(email="")

        services._send_email(user, "Title", "Body", None)

        # No exception, and nothing further to assert since send_mail is never reached.

    def test_swallows_exception_from_send_mail(self):
        user = UserFactory(email="fails@example.com")

        with patch("apps.notifications.services.send_mail", side_effect=RuntimeError("smtp down")):
            services._send_email(user, "Title", "Body", "/some-url")


@pytest.mark.django_db
class TestSendPush:
    def test_returns_false_when_vapid_not_configured(self, settings):
        settings.VAPID_PRIVATE_KEY = ""
        user = UserFactory()

        assert services._send_push(user, "Title", "Body", None) is False

    def test_deactivates_subscription_on_404(self, settings):
        settings.VAPID_PRIVATE_KEY = "test-private-key"
        user = UserFactory()
        subscription = PushSubscription.objects.create(
            user=user, endpoint="https://push.example.com/gone", p256dh_key="k", auth_key="a"
        )

        with patch(
            "apps.notifications.services.webpush",
            side_effect=WebPushException("gone", response=Mock(status_code=404)),
        ):
            sent = services._send_push(user, "Title", "Body", None)

        subscription.refresh_from_db()
        assert sent is False
        assert subscription.is_active is False

    def test_logs_and_keeps_subscription_on_other_error(self, settings):
        settings.VAPID_PRIVATE_KEY = "test-private-key"
        user = UserFactory()
        subscription = PushSubscription.objects.create(
            user=user, endpoint="https://push.example.com/error", p256dh_key="k", auth_key="a"
        )

        with patch(
            "apps.notifications.services.webpush",
            side_effect=WebPushException("server error", response=Mock(status_code=500)),
        ):
            sent = services._send_push(user, "Title", "Body", None)

        subscription.refresh_from_db()
        assert sent is False
        assert subscription.is_active is True
