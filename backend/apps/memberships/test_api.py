from decimal import Decimal

import pytest

from apps.billing.models import LedgerEntry
from apps.checkouts import services as checkout_services
from apps.common.factories import MembershipFactory, MembershipTierFactory, ToyFactory, UserFactory
from apps.notifications.models import NotificationLog

from .models import Membership


@pytest.mark.django_db
class TestMembershipTiers:
    def test_tiers_are_publicly_listable(self, api_client, silver_tier):
        res = api_client.get("/api/memberships/tiers/")

        assert res.status_code == 200
        assert any(t["code"] == "SILVER" for t in res.data["results"])

    def test_inactive_tiers_are_excluded(self, api_client, silver_tier):
        silver_tier.is_active = False
        silver_tier.save(update_fields=["is_active"])

        res = api_client.get("/api/memberships/tiers/")

        assert not any(t["code"] == "SILVER" for t in res.data["results"])

    def test_tier_listing_includes_description(self, api_client, silver_tier):
        silver_tier.description = "Great for first-time members."
        silver_tier.save(update_fields=["description"])

        res = api_client.get("/api/memberships/tiers/")

        tier = next(t for t in res.data["results"] if t["code"] == "SILVER")
        assert tier["description"] == "Great for first-time members."


@pytest.mark.django_db
class TestMyMembership:
    def test_requires_authentication(self, api_client):
        res = api_client.get("/api/memberships/me/")
        assert res.status_code == 401

    def test_404_when_no_membership(self, member_client):
        res = member_client.get("/api/memberships/me/")
        assert res.status_code == 404

    def test_returns_membership_when_present(self, member_client, active_membership):
        res = member_client.get("/api/memberships/me/")

        assert res.status_code == 200
        assert res.data["tier"]["code"] == "SILVER"


@pytest.mark.django_db
class TestMembershipSignup:
    def test_signup_creates_pending_membership_with_charges(self, member_client, silver_tier):
        res = member_client.post("/api/memberships/signup/", {"tier_code": "SILVER"})

        assert res.status_code == 201
        assert res.data["status"] == "PENDING_PAYMENT"
        membership = Membership.objects.get(id=res.data["id"])
        entries = LedgerEntry.objects.filter(related_membership=membership)
        assert entries.count() == 2
        assert {e.entry_type for e in entries} == {"JOINING_FEE", "DEPOSIT"}

    def test_signup_rejects_second_active_membership(self, member_client, active_membership, silver_tier):
        res = member_client.post("/api/memberships/signup/", {"tier_code": "SILVER"})

        assert res.status_code == 400

    def test_signup_rejects_invalid_tier_code(self, member_client):
        res = member_client.post("/api/memberships/signup/", {"tier_code": "BRONZE"})
        assert res.status_code == 400

    def test_signup_rejects_inactive_tier(self, member_client, silver_tier):
        silver_tier.is_active = False
        silver_tier.save(update_fields=["is_active"])

        res = member_client.post("/api/memberships/signup/", {"tier_code": "SILVER"})

        assert res.status_code == 400


@pytest.mark.django_db
class TestMembershipListing:
    def test_member_only_sees_own_membership(self, member_client, member, active_membership):
        other_membership = MembershipFactory()

        res = member_client.get("/api/memberships/")

        ids = {m["id"] for m in res.data["results"]}
        assert str(active_membership.id) in ids
        assert str(other_membership.id) not in ids

    def test_staff_sees_all_memberships(self, staff_client, active_membership):
        other_membership = MembershipFactory()

        res = staff_client.get("/api/memberships/")

        ids = {m["id"] for m in res.data["results"]}
        assert str(active_membership.id) in ids
        assert str(other_membership.id) in ids


@pytest.mark.django_db
class TestActivate:
    def test_staff_can_activate_pending_membership(self, staff_client, member, silver_tier):
        membership = MembershipFactory(user=member, tier=silver_tier, status=Membership.Status.PENDING_PAYMENT, joined_at=None, renewed_through=None)

        res = staff_client.post(f"/api/memberships/{membership.id}/activate/")

        assert res.status_code == 200
        assert res.data["status"] == "ACTIVE"

    def test_member_cannot_activate(self, member_client, silver_tier):
        membership = MembershipFactory(tier=silver_tier, status=Membership.Status.PENDING_PAYMENT, joined_at=None, renewed_through=None)

        res = member_client.post(f"/api/memberships/{membership.id}/activate/")

        assert res.status_code == 403

    def test_activate_already_active_membership_fails(self, staff_client, active_membership):
        res = staff_client.post(f"/api/memberships/{active_membership.id}/activate/")
        assert res.status_code == 400


@pytest.mark.django_db
class TestNudge:
    def test_member_can_nudge_staff_about_own_pending_membership(self, member_client, member, silver_tier):
        membership = MembershipFactory(user=member, tier=silver_tier, status=Membership.Status.PENDING_PAYMENT)
        staff = UserFactory(is_staff=True)

        res = member_client.post(f"/api/memberships/{membership.id}/nudge/")

        assert res.status_code == 204
        assert NotificationLog.objects.filter(
            user=staff, event_type="MEMBERSHIP_APPROVAL_REQUESTED"
        ).exists()

    def test_member_cannot_nudge_about_someone_elses_membership(self, member_client):
        other_membership = MembershipFactory(status=Membership.Status.PENDING_PAYMENT)

        res = member_client.post(f"/api/memberships/{other_membership.id}/nudge/")

        assert res.status_code == 404

    def test_nudge_rejects_already_active_membership(self, member_client, active_membership):
        res = member_client.post(f"/api/memberships/{active_membership.id}/nudge/")

        assert res.status_code == 400

    def test_nudge_requires_authentication(self, api_client, silver_tier):
        membership = MembershipFactory(tier=silver_tier, status=Membership.Status.PENDING_PAYMENT)

        res = api_client.post(f"/api/memberships/{membership.id}/nudge/")

        assert res.status_code == 401


@pytest.mark.django_db
class TestChangeTier:
    def test_staff_can_change_member_tier(self, staff_client, active_membership):
        MembershipTierFactory(code="DIAMOND", deposit_amount=Decimal("80.00"))

        res = staff_client.post(
            f"/api/memberships/{active_membership.id}/change-tier/", {"new_tier_code": "DIAMOND"}
        )

        assert res.status_code == 200

    def test_admin_can_change_member_tier(self, admin_client, active_membership):
        MembershipTierFactory(code="DIAMOND", deposit_amount=Decimal("80.00"))

        res = admin_client.post(
            f"/api/memberships/{active_membership.id}/change-tier/", {"new_tier_code": "DIAMOND"}
        )

        assert res.status_code == 200

    def test_member_cannot_change_own_tier(self, member_client, active_membership):
        MembershipTierFactory(code="DIAMOND", deposit_amount=Decimal("80.00"))

        res = member_client.post(
            f"/api/memberships/{active_membership.id}/change-tier/", {"new_tier_code": "DIAMOND"}
        )

        assert res.status_code == 403

    def test_change_tier_rejects_same_tier(self, staff_client, active_membership):
        res = staff_client.post(
            f"/api/memberships/{active_membership.id}/change-tier/",
            {"new_tier_code": active_membership.tier.code},
        )
        assert res.status_code == 400


@pytest.mark.django_db
class TestMembershipTermination:
    def test_staff_can_request_termination(self, staff_client, active_membership):
        res = staff_client.post(f"/api/memberships/{active_membership.id}/request-termination/")

        assert res.status_code == 201
        assert res.data["status"] == "REQUESTED"
        active_membership.refresh_from_db()
        assert active_membership.status == "PENDING_TERMINATION"

    def test_request_termination_blocked_while_toy_checked_out(self, staff_client, active_membership):
        toy = ToyFactory()
        checkout_services.create_checkout(toy, active_membership.user, active_membership.user)

        res = staff_client.post(f"/api/memberships/{active_membership.id}/request-termination/")

        assert res.status_code == 400

    def test_member_cannot_request_termination(self, member_client, active_membership):
        res = member_client.post(f"/api/memberships/{active_membership.id}/request-termination/")
        assert res.status_code == 403

    def test_staff_cannot_approve_termination(self, staff_client, active_membership):
        staff_client.post(f"/api/memberships/{active_membership.id}/request-termination/")

        res = staff_client.post(
            f"/api/memberships/{active_membership.id}/approve-termination/", {"approve": True}
        )

        assert res.status_code == 403

    def test_admin_can_approve_then_staff_refunds(self, staff_client, admin_client, active_membership):
        staff_client.post(f"/api/memberships/{active_membership.id}/request-termination/")

        approve_res = admin_client.post(
            f"/api/memberships/{active_membership.id}/approve-termination/", {"approve": True}
        )
        assert approve_res.status_code == 200
        assert approve_res.data["status"] == "APPROVED"

        refund_res = staff_client.post(
            f"/api/memberships/{active_membership.id}/refund-deposit/",
            {"amount_returned": "50.00", "notes": ""},
        )
        assert refund_res.status_code == 200
        assert refund_res.data["status"] == "REFUNDED"
        active_membership.refresh_from_db()
        assert active_membership.status == "DISCONTINUED"

    def test_refund_before_approval_fails(self, staff_client, active_membership):
        staff_client.post(f"/api/memberships/{active_membership.id}/request-termination/")

        res = staff_client.post(
            f"/api/memberships/{active_membership.id}/refund-deposit/",
            {"amount_returned": "50.00", "notes": ""},
        )
        assert res.status_code == 400

    def test_admin_can_reject_termination(self, staff_client, admin_client, active_membership):
        staff_client.post(f"/api/memberships/{active_membership.id}/request-termination/")

        res = admin_client.post(
            f"/api/memberships/{active_membership.id}/approve-termination/",
            {"approve": False, "reason": "Needs manager review"},
        )

        assert res.status_code == 200
        assert res.data["status"] == "REJECTED"
        active_membership.refresh_from_db()
        assert active_membership.status == "ACTIVE"
