import pytest

from apps.common.factories import UserFactory

from .models import NotificationLog, PushSubscription


@pytest.mark.django_db
class TestNotificationList:
    def test_requires_authentication(self, api_client):
        res = api_client.get("/api/notifications/")
        assert res.status_code == 401

    def test_member_only_sees_own_notifications(self, member_client, member):
        NotificationLog.objects.create(
            user=member, event_type="DUE_DATE_REMINDER", channel="IN_APP", title="Hi"
        )
        NotificationLog.objects.create(
            user=UserFactory(), event_type="DUE_DATE_REMINDER", channel="IN_APP", title="Other"
        )

        res = member_client.get("/api/notifications/")

        assert len(res.data["results"]) == 1

    def test_mark_read(self, member_client, member):
        log = NotificationLog.objects.create(
            user=member, event_type="DUE_DATE_REMINDER", channel="IN_APP", title="Hi"
        )

        res = member_client.post(f"/api/notifications/{log.id}/mark-read/")

        assert res.status_code == 200
        assert res.data["read_at"] is not None

    def test_cannot_mark_read_someone_elses_notification(self, member_client):
        log = NotificationLog.objects.create(
            user=UserFactory(), event_type="DUE_DATE_REMINDER", channel="IN_APP", title="Other"
        )

        res = member_client.post(f"/api/notifications/{log.id}/mark-read/")

        assert res.status_code == 404


@pytest.mark.django_db
class TestNotificationPreferences:
    def test_get_creates_default_preference(self, member_client):
        res = member_client.get("/api/notification-preferences/me/")

        assert res.status_code == 200
        assert res.data["email_enabled"] is True
        assert res.data["push_enabled"] is True

    def test_patch_updates_preference(self, member_client):
        res = member_client.patch("/api/notification-preferences/me/", {"push_enabled": False})

        assert res.status_code == 200
        assert res.data["push_enabled"] is False

    def test_requires_authentication(self, api_client):
        res = api_client.get("/api/notification-preferences/me/")
        assert res.status_code == 401


@pytest.mark.django_db
class TestPushSubscriptions:
    def test_member_can_register_subscription(self, member_client, member):
        res = member_client.post(
            "/api/push-subscriptions/",
            {
                "endpoint": "https://push.example.com/abc123",
                "p256dh_key": "key1",
                "auth_key": "key2",
            },
        )

        assert res.status_code == 201
        assert PushSubscription.objects.filter(user=member, endpoint="https://push.example.com/abc123").exists()

    def test_resubscribing_same_endpoint_updates_rather_than_duplicates(self, member_client, member):
        payload = {
            "endpoint": "https://push.example.com/abc123",
            "p256dh_key": "key1",
            "auth_key": "key2",
        }
        member_client.post("/api/push-subscriptions/", payload)
        member_client.post("/api/push-subscriptions/", payload)

        assert PushSubscription.objects.filter(endpoint="https://push.example.com/abc123").count() == 1

    def test_member_can_delete_own_subscription(self, member_client, member):
        sub = PushSubscription.objects.create(
            user=member, endpoint="https://push.example.com/xyz", p256dh_key="a", auth_key="b"
        )

        res = member_client.delete(f"/api/push-subscriptions/{sub.id}/")

        assert res.status_code == 204
        assert not PushSubscription.objects.filter(id=sub.id).exists()

    def test_member_cannot_delete_others_subscription(self, member_client):
        sub = PushSubscription.objects.create(
            user=UserFactory(), endpoint="https://push.example.com/other", p256dh_key="a", auth_key="b"
        )

        res = member_client.delete(f"/api/push-subscriptions/{sub.id}/")

        assert res.status_code == 404
