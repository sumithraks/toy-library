import pytest

from .models import Donation, DonationItem


@pytest.mark.django_db
class TestSubmitDonation:
    def test_anonymous_can_submit_donation(self, api_client):
        res = api_client.post(
            "/api/donations/",
            {
                "donor": {"name": "Jane Donor", "email": "jane@example.com"},
                "items": [{"item_type": "BOARD_GAME", "description": "Chess set", "make": "X", "model_name": "Y"}],
            },
            format="json",
        )

        assert res.status_code == 201
        assert res.data["status"] == "SUBMITTED"
        assert len(res.data["items"]) == 1

    def test_soft_toy_donation_is_rejected(self, api_client):
        res = api_client.post(
            "/api/donations/",
            {
                "donor": {"name": "Jane Donor"},
                "items": [{"item_type": "SOFT_TOY", "description": "Teddy bear"}],
            },
            format="json",
        )

        assert res.status_code == 400

    def test_doll_donation_is_rejected(self, api_client):
        res = api_client.post(
            "/api/donations/",
            {"donor": {"name": "Jane Donor"}, "items": [{"item_type": "DOLL", "description": "Barbie"}]},
            format="json",
        )

        assert res.status_code == 400

    def test_mixed_batch_with_one_disallowed_item_is_fully_rejected(self, api_client):
        res = api_client.post(
            "/api/donations/",
            {
                "donor": {"name": "Jane Donor"},
                "items": [
                    {"item_type": "PUZZLE", "description": "1000pc puzzle"},
                    {"item_type": "DOLL", "description": "Barbie"},
                ],
            },
            format="json",
        )

        assert res.status_code == 400
        assert Donation.objects.count() == 0


@pytest.mark.django_db
class TestDonationListing:
    def test_list_requires_authentication(self, api_client):
        res = api_client.get("/api/donations/")
        assert res.status_code == 401

    def test_staff_can_list_donations(self, staff_client, api_client):
        api_client.post(
            "/api/donations/",
            {"donor": {"name": "Jane"}, "items": [{"item_type": "PUZZLE", "description": "x"}]},
            format="json",
        )

        res = staff_client.get("/api/donations/")

        assert res.status_code == 200
        assert len(res.data["results"]) == 1

    def test_member_only_sees_own_donations(self, member_client, member, staff_client):
        member_client.post(
            "/api/donations/",
            {"donor": {"name": "Own Donation"}, "items": [{"item_type": "PUZZLE", "description": "x"}]},
            format="json",
        )
        staff_client.post(
            "/api/donations/",
            {"donor": {"name": "Someone Else"}, "items": [{"item_type": "PUZZLE", "description": "y"}]},
            format="json",
        )

        res = member_client.get("/api/donations/")

        assert res.status_code == 200
        assert len(res.data["results"]) == 1
        assert res.data["results"][0]["donor"]["name"] == "Own Donation"


@pytest.mark.django_db
class TestAcceptRejectDonation:
    def _submit(self, api_client):
        res = api_client.post(
            "/api/donations/",
            {"donor": {"name": "Jane"}, "items": [{"item_type": "PUZZLE", "description": "x"}]},
            format="json",
        )
        return res.data["id"]

    def test_member_cannot_accept(self, api_client, member_client):
        donation_id = self._submit(api_client)
        res = member_client.post(f"/api/donations/{donation_id}/accept/")
        assert res.status_code == 403

    def test_staff_can_accept_and_receipt_is_issued(self, api_client, staff_client):
        donation_id = self._submit(api_client)

        res = staff_client.post(f"/api/donations/{donation_id}/accept/")

        assert res.status_code == 200
        assert res.data["status"] == "IN_INTAKE"

        receipt_res = staff_client.get(f"/api/donations/{donation_id}/receipt/")
        assert receipt_res.status_code == 200
        assert receipt_res.data["receipt_number"].startswith("DON-")

    def test_staff_can_reject_with_reason(self, api_client, staff_client):
        donation_id = self._submit(api_client)

        res = staff_client.post(f"/api/donations/{donation_id}/reject/", {"reason": "Not needed"})

        assert res.status_code == 200
        assert res.data["status"] == "REJECTED"
        assert res.data["rejection_reason"] == "Not needed"

    def test_cannot_accept_already_accepted_donation(self, api_client, staff_client):
        donation_id = self._submit(api_client)
        staff_client.post(f"/api/donations/{donation_id}/accept/")

        res = staff_client.post(f"/api/donations/{donation_id}/accept/")

        assert res.status_code == 400

    def test_receipt_404_before_acceptance(self, api_client, staff_client):
        donation_id = self._submit(api_client)

        res = staff_client.get(f"/api/donations/{donation_id}/receipt/")

        assert res.status_code == 404


@pytest.mark.django_db
class TestCompleteIntake:
    def test_staff_completes_intake_and_toy_becomes_available(self, api_client, staff_client):
        submit_res = api_client.post(
            "/api/donations/",
            {"donor": {"name": "Jane"}, "items": [{"item_type": "PUZZLE", "description": "x", "make": "Acme", "model_name": "Puzzle 1"}]},
            format="json",
        )
        donation_id = submit_res.data["id"]
        staff_client.post(f"/api/donations/{donation_id}/accept/")
        item_id = DonationItem.objects.get(donation_id=donation_id).id

        res = staff_client.post(
            f"/api/donations/{donation_id}/items/{item_id}/complete-intake/",
            {"condition": "LIGHTLY_USED", "age_rating": "3+"},
        )

        assert res.status_code == 201
        assert res.data["status"] == "AVAILABLE"
        assert res.data["source"] == "DONATED"

        donation = Donation.objects.get(id=donation_id)
        assert donation.status == "COMPLETED"

    def test_damaged_intake_marks_toy_broken(self, api_client, staff_client):
        submit_res = api_client.post(
            "/api/donations/",
            {"donor": {"name": "Jane"}, "items": [{"item_type": "PUZZLE", "description": "x"}]},
            format="json",
        )
        donation_id = submit_res.data["id"]
        staff_client.post(f"/api/donations/{donation_id}/accept/")
        item_id = DonationItem.objects.get(donation_id=donation_id).id

        res = staff_client.post(
            f"/api/donations/{donation_id}/items/{item_id}/complete-intake/",
            {"condition": "DAMAGED"},
        )

        assert res.status_code == 201
        assert res.data["status"] == "BROKEN"

    def test_member_cannot_complete_intake(self, api_client, member_client, staff_client):
        submit_res = api_client.post(
            "/api/donations/",
            {"donor": {"name": "Jane"}, "items": [{"item_type": "PUZZLE", "description": "x"}]},
            format="json",
        )
        donation_id = submit_res.data["id"]
        staff_client.post(f"/api/donations/{donation_id}/accept/")
        item_id = DonationItem.objects.get(donation_id=donation_id).id

        res = member_client.post(
            f"/api/donations/{donation_id}/items/{item_id}/complete-intake/",
            {"condition": "LIGHTLY_USED"},
        )

        assert res.status_code == 403
