from decimal import Decimal

import pytest

from apps.checkouts import services as checkout_services
from apps.checkouts.models import CheckoutRecord
from apps.common.factories import MembershipFactory, ToyFactory, UserFactory
from apps.inventory.models import Toy


@pytest.mark.django_db
class TestCreateCheckout:
    def test_staff_can_check_out_a_toy(self, staff_client, active_membership, toy):
        res = staff_client.post(
            "/api/checkouts/", {"toy": str(toy.id), "member": str(active_membership.user.id)}
        )

        assert res.status_code == 201
        assert res.data["status"] == "ACTIVE"
        assert res.data["complimentary_extension_available"] is True

    def test_member_cannot_self_checkout(self, member_client, active_membership, toy):
        res = member_client.post(
            "/api/checkouts/", {"toy": str(toy.id), "member": str(active_membership.user.id)}
        )
        assert res.status_code == 403

    def test_rejects_when_over_tier_limit(self, staff_client, active_membership):
        toy1, toy2 = ToyFactory(), ToyFactory()
        staff_client.post(
            "/api/checkouts/", {"toy": str(toy1.id), "member": str(active_membership.user.id)}
        )

        res = staff_client.post(
            "/api/checkouts/", {"toy": str(toy2.id), "member": str(active_membership.user.id)}
        )

        assert res.status_code == 400


@pytest.mark.django_db
class TestListCheckouts:
    def test_member_only_sees_own_checkouts(self, member_client, member, staff_user):
        toy1, toy2 = ToyFactory(), ToyFactory()
        membership1 = MembershipFactory(user=member)
        other_member = UserFactory()
        membership2 = MembershipFactory(user=other_member)
        checkout1 = checkout_services.create_checkout(toy1, member, staff_user)
        checkout_services.create_checkout(toy2, other_member, staff_user)

        res = member_client.get("/api/checkouts/")

        ids = {c["id"] for c in res.data["results"]}
        assert ids == {str(checkout1.id)}

    def test_staff_sees_all_checkouts(self, staff_client, staff_user):
        toy1, toy2 = ToyFactory(), ToyFactory()
        m1, m2 = MembershipFactory(), MembershipFactory()
        checkout_services.create_checkout(toy1, m1.user, staff_user)
        checkout_services.create_checkout(toy2, m2.user, staff_user)

        res = staff_client.get("/api/checkouts/")

        assert len(res.data["results"]) == 2


@pytest.mark.django_db
class TestReturnCheckout:
    def test_staff_can_return_a_checkout(self, staff_client, staff_user, active_membership, toy):
        checkout = checkout_services.create_checkout(toy, active_membership.user, staff_user)

        res = staff_client.post(
            f"/api/checkouts/{checkout.id}/return/", {"condition": "LIGHTLY_USED"}
        )

        assert res.status_code == 200
        assert res.data["status"] == "RETURNED"

    def test_member_cannot_return_a_checkout(self, member_client, staff_user, active_membership, toy):
        checkout = checkout_services.create_checkout(toy, active_membership.user, staff_user)

        res = member_client.post(
            f"/api/checkouts/{checkout.id}/return/", {"condition": "LIGHTLY_USED"}
        )
        assert res.status_code == 403

    def test_damaged_return_requires_valid_damaged_status(self, staff_client, staff_user, active_membership, toy):
        checkout = checkout_services.create_checkout(toy, active_membership.user, staff_user)

        res = staff_client.post(
            f"/api/checkouts/{checkout.id}/return/",
            {"condition": "DAMAGED", "damaged_status": "UNDER_REPAIR"},
        )

        assert res.status_code == 200
        toy.refresh_from_db()
        assert toy.status == "UNDER_REPAIR"


@pytest.mark.django_db
class TestComplimentaryExtension:
    def test_owner_can_extend(self, member_client, member, staff_user, silver_tier, toy):
        membership = MembershipFactory(user=member, tier=silver_tier)
        checkout = checkout_services.create_checkout(toy, member, staff_user)
        original_due = checkout.current_due_date

        res = member_client.post(f"/api/checkouts/{checkout.id}/extend/complimentary/")

        assert res.status_code == 200
        assert res.data["current_due_date"] != str(original_due)
        assert res.data["complimentary_extension_used"] is True

    def test_non_owner_member_cannot_extend(self, api_client, staff_user, active_membership, toy):
        # Non-staff get_queryset() is scoped to member=self.request.user, so a
        # non-owner's checkout lookup 404s before the object-permission check runs.
        checkout = checkout_services.create_checkout(toy, active_membership.user, staff_user)
        other_member = UserFactory()
        api_client.force_authenticate(user=other_member)

        res = api_client.post(f"/api/checkouts/{checkout.id}/extend/complimentary/")

        assert res.status_code == 404

    def test_staff_can_extend_on_behalf_of_member(self, staff_client, staff_user, active_membership, toy):
        checkout = checkout_services.create_checkout(toy, active_membership.user, staff_user)

        res = staff_client.post(f"/api/checkouts/{checkout.id}/extend/complimentary/")

        assert res.status_code == 200

    def test_cannot_extend_twice(self, member_client, member, staff_user, silver_tier, toy):
        MembershipFactory(user=member, tier=silver_tier)
        checkout = checkout_services.create_checkout(toy, member, staff_user)
        member_client.post(f"/api/checkouts/{checkout.id}/extend/complimentary/")

        res = member_client.post(f"/api/checkouts/{checkout.id}/extend/complimentary/")

        assert res.status_code == 400

    def test_blocked_once_overdue(self, member_client, member, staff_user, silver_tier, toy):
        MembershipFactory(user=member, tier=silver_tier)
        checkout = checkout_services.create_checkout(toy, member, staff_user)
        checkout.status = CheckoutRecord.Status.OVERDUE
        checkout.save(update_fields=["status"])

        res = member_client.post(f"/api/checkouts/{checkout.id}/extend/complimentary/")

        assert res.status_code == 400


@pytest.mark.django_db
class TestPaidExtension:
    def test_owner_can_request_paid_extension(self, member_client, member, staff_user, active_membership, toy):
        checkout = checkout_services.create_checkout(toy, member, staff_user)

        res = member_client.post(f"/api/checkouts/{checkout.id}/extend/paid/", {"days": 5})

        assert res.status_code == 201
        assert res.data["extension_type"] == "PAID"
        assert res.data["applied"] is False

    def test_due_date_unchanged_until_marked_paid(self, staff_client, staff_user, active_membership, toy):
        checkout = checkout_services.create_checkout(toy, active_membership.user, staff_user)
        original_due = checkout.current_due_date

        res = staff_client.post(f"/api/checkouts/{checkout.id}/extend/paid/", {"days": 5})
        assert res.status_code == 201

        checkout.refresh_from_db()
        assert checkout.current_due_date == original_due

    def test_non_owner_member_gets_404_not_403(self, api_client, staff_user, active_membership, toy):
        # extend/paid uses IsAuthenticated only; the member-scoped queryset in
        # get_queryset() is what actually prevents cross-member access.
        checkout = checkout_services.create_checkout(toy, active_membership.user, staff_user)
        other_member = UserFactory()
        api_client.force_authenticate(user=other_member)

        res = api_client.post(f"/api/checkouts/{checkout.id}/extend/paid/", {"days": 5})

        assert res.status_code == 404

    def test_rejects_more_than_30_days(self, member_client, staff_user, active_membership, toy):
        checkout = checkout_services.create_checkout(toy, active_membership.user, staff_user)
        res = member_client.post(f"/api/checkouts/{checkout.id}/extend/paid/", {"days": 100})
        assert res.status_code == 400


@pytest.mark.django_db
class TestExtensionsList:
    def test_lists_extensions_for_a_checkout(self, staff_client, staff_user, active_membership, toy):
        checkout = checkout_services.create_checkout(toy, active_membership.user, staff_user)
        checkout_services.apply_paid_extension(checkout, 3, staff_user)

        res = staff_client.get(f"/api/checkouts/{checkout.id}/extensions/")

        assert res.status_code == 200
        assert len(res.data) == 1
        assert res.data[0]["days_added"] == 3
