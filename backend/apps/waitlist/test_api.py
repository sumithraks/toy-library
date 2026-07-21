import pytest

from apps.common.factories import ToyFactory, UserFactory

from .models import WaitlistEntry


@pytest.mark.django_db
class TestJoinWaitlist:
    def test_requires_authentication(self, api_client, toy):
        res = api_client.post("/api/waitlist/", {"toy": str(toy.id)})
        assert res.status_code == 401

    def test_member_can_join_waitlist(self, member_client, toy):
        res = member_client.post("/api/waitlist/", {"toy": str(toy.id)})

        assert res.status_code == 201
        assert res.data["status"] == "WAITING"

    def test_cannot_join_same_waitlist_twice(self, member_client, toy):
        member_client.post("/api/waitlist/", {"toy": str(toy.id)})

        res = member_client.post("/api/waitlist/", {"toy": str(toy.id)})

        assert res.status_code == 400


@pytest.mark.django_db
class TestListWaitlist:
    def test_member_only_sees_own_entries(self, member_client, member, toy):
        WaitlistEntry.objects.create(toy=toy, user=member)
        other_toy = ToyFactory()
        WaitlistEntry.objects.create(toy=other_toy, user=UserFactory())

        res = member_client.get("/api/waitlist/")

        assert len(res.data["results"]) == 1

    def test_staff_sees_all_entries(self, staff_client, member, toy):
        WaitlistEntry.objects.create(toy=toy, user=member)
        WaitlistEntry.objects.create(toy=ToyFactory(), user=UserFactory())

        res = staff_client.get("/api/waitlist/")

        assert len(res.data["results"]) == 2


@pytest.mark.django_db
class TestLeaveWaitlist:
    def test_member_can_leave_own_waitlist_entry(self, member_client, member, toy):
        entry = WaitlistEntry.objects.create(toy=toy, user=member)

        res = member_client.delete(f"/api/waitlist/{entry.id}/")

        assert res.status_code == 204
        entry.refresh_from_db()
        assert entry.status == "CANCELLED"

    def test_member_cannot_see_or_leave_others_entry(self, member_client, toy):
        entry = WaitlistEntry.objects.create(toy=toy, user=UserFactory())

        res = member_client.delete(f"/api/waitlist/{entry.id}/")

        assert res.status_code == 404
