from decimal import Decimal

import pytest

from apps.common.factories import UserFactory

from . import services
from .models import LedgerEntry


@pytest.mark.django_db
class TestGetUserBalance:
    def test_balance_is_charges_minus_credits_for_pending_entries_only(self):
        user = UserFactory()
        services.create_ledger_entry(
            user=user,
            entry_type=LedgerEntry.EntryType.LATE_FEE,
            amount=Decimal("10.00"),
            direction=LedgerEntry.Direction.CHARGE,
        )
        services.create_ledger_entry(
            user=user,
            entry_type=LedgerEntry.EntryType.DEPOSIT_REFUND,
            amount=Decimal("3.00"),
            direction=LedgerEntry.Direction.CREDIT,
        )
        # A PAID charge should not affect the pending balance.
        services.create_ledger_entry(
            user=user,
            entry_type=LedgerEntry.EntryType.LATE_FEE,
            amount=Decimal("100.00"),
            direction=LedgerEntry.Direction.CHARGE,
            status=LedgerEntry.Status.PAID,
        )

        assert services.get_user_balance(user) == Decimal("7.00")

    def test_balance_is_zero_with_no_entries(self):
        user = UserFactory()

        assert services.get_user_balance(user) == Decimal("0.00")
