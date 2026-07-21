from decimal import Decimal

import pytest

from apps.billing.models import LedgerEntry
from apps.billing.services import create_ledger_entry
from apps.common.factories import UserFactory


@pytest.mark.django_db
class TestLedgerEntryList:
    def test_requires_authentication(self, api_client):
        res = api_client.get("/api/ledger-entries/")
        assert res.status_code == 401

    def test_member_only_sees_own_entries(self, member_client, member):
        create_ledger_entry(
            user=member,
            entry_type=LedgerEntry.EntryType.LATE_FEE,
            amount=Decimal("1.00"),
            direction=LedgerEntry.Direction.CHARGE,
        )
        other_user = UserFactory()
        create_ledger_entry(
            user=other_user,
            entry_type=LedgerEntry.EntryType.LATE_FEE,
            amount=Decimal("2.00"),
            direction=LedgerEntry.Direction.CHARGE,
        )

        res = member_client.get("/api/ledger-entries/")

        assert res.status_code == 200
        assert len(res.data["results"]) == 1
        assert res.data["results"][0]["amount"] == "1.00"

    def test_staff_sees_all_entries(self, staff_client, member):
        create_ledger_entry(
            user=member,
            entry_type=LedgerEntry.EntryType.LATE_FEE,
            amount=Decimal("1.00"),
            direction=LedgerEntry.Direction.CHARGE,
        )

        res = staff_client.get("/api/ledger-entries/")

        assert res.status_code == 200
        assert len(res.data["results"]) == 1

    def test_status_filter(self, member_client, member):
        pending = create_ledger_entry(
            user=member,
            entry_type=LedgerEntry.EntryType.LATE_FEE,
            amount=Decimal("1.00"),
            direction=LedgerEntry.Direction.CHARGE,
        )
        create_ledger_entry(
            user=member,
            entry_type=LedgerEntry.EntryType.LATE_FEE,
            amount=Decimal("2.00"),
            direction=LedgerEntry.Direction.CHARGE,
            status=LedgerEntry.Status.PAID,
        )

        res = member_client.get("/api/ledger-entries/?status=PENDING")

        assert res.status_code == 200
        ids = {e["id"] for e in res.data["results"]}
        assert ids == {str(pending.id)}


@pytest.mark.django_db
class TestMarkPaid:
    def test_staff_can_mark_paid(self, staff_client, staff_user, member):
        entry = create_ledger_entry(
            user=member,
            entry_type=LedgerEntry.EntryType.LATE_FEE,
            amount=Decimal("1.00"),
            direction=LedgerEntry.Direction.CHARGE,
        )

        res = staff_client.post(f"/api/ledger-entries/{entry.id}/mark-paid/")

        assert res.status_code == 200
        assert res.data["status"] == "PAID"

    def test_member_cannot_mark_paid(self, member_client, member):
        entry = create_ledger_entry(
            user=member,
            entry_type=LedgerEntry.EntryType.LATE_FEE,
            amount=Decimal("1.00"),
            direction=LedgerEntry.Direction.CHARGE,
        )

        res = member_client.post(f"/api/ledger-entries/{entry.id}/mark-paid/")

        assert res.status_code == 403

    def test_cannot_mark_already_paid_entry_paid_again(self, staff_client, member):
        entry = create_ledger_entry(
            user=member,
            entry_type=LedgerEntry.EntryType.LATE_FEE,
            amount=Decimal("1.00"),
            direction=LedgerEntry.Direction.CHARGE,
            status=LedgerEntry.Status.PAID,
        )

        res = staff_client.post(f"/api/ledger-entries/{entry.id}/mark-paid/")

        assert res.status_code == 400
