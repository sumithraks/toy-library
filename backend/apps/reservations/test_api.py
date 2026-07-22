from datetime import timedelta

import pytest
from django.utils import timezone

from apps.common.factories import UserFactory

from .models import Reservation
from .services import create_reservation


@pytest.mark.django_db
class TestCreateReservation:
    def test_member_can_reserve_an_available_toy(self, member_client, toy):
        pickup_by = (timezone.now().date() + timedelta(days=1)).isoformat()

        res = member_client.post(
            "/api/reservations/", {"toy": str(toy.id), "pickup_by_date": pickup_by}
        )

        assert res.status_code == 201
        assert res.data["status"] == "ACTIVE"
        toy.refresh_from_db()
        assert toy.status == "RESERVED"

    def test_rejects_pickup_date_beyond_2_days(self, member_client, toy):
        pickup_by = (timezone.now().date() + timedelta(days=5)).isoformat()

        res = member_client.post(
            "/api/reservations/", {"toy": str(toy.id), "pickup_by_date": pickup_by}
        )

        assert res.status_code == 400

    def test_cannot_reserve_unavailable_toy(self, member_client, toy):
        pickup_by = (timezone.now().date() + timedelta(days=1)).isoformat()
        member_client.post("/api/reservations/", {"toy": str(toy.id), "pickup_by_date": pickup_by})
        other_member_client = member_client
        # toy is now RESERVED; a second reservation attempt should fail
        res = other_member_client.post(
            "/api/reservations/", {"toy": str(toy.id), "pickup_by_date": pickup_by}
        )

        assert res.status_code == 400


@pytest.mark.django_db
class TestListReservations:
    def test_member_only_sees_own_reservations(self, member_client, member, toy):
        create_reservation(toy, member, timezone.now().date() + timedelta(days=1))
        from apps.common.factories import ToyFactory

        create_reservation(ToyFactory(), UserFactory(), timezone.now().date() + timedelta(days=1))

        res = member_client.get("/api/reservations/")

        assert len(res.data["results"]) == 1

    def test_staff_can_filter_by_status(self, staff_client, active_membership, toy):
        from apps.common.factories import ToyFactory

        active = create_reservation(
            toy, active_membership.user, timezone.now().date() + timedelta(days=1)
        )
        picked_up = create_reservation(
            ToyFactory(), active_membership.user, timezone.now().date() + timedelta(days=1)
        )
        staff_client.post(f"/api/reservations/{picked_up.id}/confirm-pickup/")

        res = staff_client.get("/api/reservations/?status=ACTIVE")

        ids = {r["id"] for r in res.data["results"]}
        assert str(active.id) in ids
        assert str(picked_up.id) not in ids


@pytest.mark.django_db
class TestCancelReservation:
    def test_owner_can_cancel(self, member_client, member, toy):
        reservation = create_reservation(toy, member, timezone.now().date() + timedelta(days=1))

        res = member_client.post(f"/api/reservations/{reservation.id}/cancel/")

        assert res.status_code == 200
        assert res.data["status"] == "CANCELLED"
        toy.refresh_from_db()
        assert toy.status == "AVAILABLE"

    def test_non_owner_cannot_see_or_cancel(self, member_client, toy):
        reservation = create_reservation(toy, UserFactory(), timezone.now().date() + timedelta(days=1))

        res = member_client.post(f"/api/reservations/{reservation.id}/cancel/")

        assert res.status_code == 404


@pytest.mark.django_db
class TestConfirmPickup:
    def test_staff_confirms_pickup_and_creates_checkout(self, staff_client, active_membership, toy):
        reservation = create_reservation(
            toy, active_membership.user, timezone.now().date() + timedelta(days=1)
        )

        res = staff_client.post(f"/api/reservations/{reservation.id}/confirm-pickup/")

        assert res.status_code == 200
        assert res.data["status"] == "PICKED_UP"
        assert res.data["resulting_checkout"] is not None
        toy.refresh_from_db()
        assert toy.status == "CHECKED_OUT"

    def test_member_cannot_confirm_pickup(self, member_client, member, toy):
        reservation = create_reservation(toy, member, timezone.now().date() + timedelta(days=1))

        res = member_client.post(f"/api/reservations/{reservation.id}/confirm-pickup/")

        assert res.status_code == 403

    def test_cannot_confirm_already_picked_up_reservation(self, staff_client, active_membership, toy):
        reservation = create_reservation(
            toy, active_membership.user, timezone.now().date() + timedelta(days=1)
        )
        staff_client.post(f"/api/reservations/{reservation.id}/confirm-pickup/")

        res = staff_client.post(f"/api/reservations/{reservation.id}/confirm-pickup/")

        assert res.status_code == 400
