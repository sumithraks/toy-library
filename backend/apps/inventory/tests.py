import pytest

from apps.common.factories import ToyFactory, UserFactory
from apps.inventory import services
from apps.inventory.models import IntakeRecord, Toy, ToyStatusLog


@pytest.mark.django_db
def test_valid_transition_updates_status_and_logs():
    toy = ToyFactory(status=Toy.Status.INTAKE)
    staff = UserFactory(is_staff=True)

    services.transition_toy_status(toy, Toy.Status.AVAILABLE, actor=staff, reason="Stocked")
    toy.refresh_from_db()

    assert toy.status == Toy.Status.AVAILABLE
    log = ToyStatusLog.objects.get(toy=toy)
    assert log.from_status == Toy.Status.INTAKE
    assert log.to_status == Toy.Status.AVAILABLE
    assert log.changed_by == staff


@pytest.mark.django_db
def test_illegal_transition_is_rejected():
    toy = ToyFactory(status=Toy.Status.RETIRED)

    with pytest.raises(ValueError, match="Cannot transition"):
        services.transition_toy_status(toy, Toy.Status.AVAILABLE)


@pytest.mark.django_db
def test_overdue_only_reachable_from_checked_out():
    toy = ToyFactory(status=Toy.Status.AVAILABLE)

    with pytest.raises(ValueError):
        services.transition_toy_status(toy, Toy.Status.OVERDUE)


@pytest.mark.django_db
def test_intake_toy_creates_toy_intake_record_and_marks_available():
    staff = UserFactory(is_staff=True)

    toy = services.intake_toy(
        model_name="Wooden Blocks",
        make="Acme",
        condition=Toy.Condition.LIGHTLY_USED,
        intake_type=IntakeRecord.IntakeType.INITIAL_PURCHASE,
        staff_user=staff,
    )

    assert toy.status == Toy.Status.AVAILABLE
    record = IntakeRecord.objects.get(toy=toy)
    assert record.intake_type == IntakeRecord.IntakeType.INITIAL_PURCHASE
    assert record.assessed_condition == Toy.Condition.LIGHTLY_USED
    assert record.assessed_by == staff
    log = ToyStatusLog.objects.get(toy=toy)
    assert log.from_status == Toy.Status.INTAKE
    assert log.to_status == Toy.Status.AVAILABLE


@pytest.mark.django_db
def test_intake_toy_marks_damaged_items_broken():
    staff = UserFactory(is_staff=True)

    toy = services.intake_toy(
        model_name="Cracked Puzzle",
        make="Acme",
        condition=Toy.Condition.DAMAGED,
        intake_type=IntakeRecord.IntakeType.INITIAL_PURCHASE,
        staff_user=staff,
    )

    assert toy.status == Toy.Status.BROKEN


@pytest.mark.django_db
def test_intake_purchased_toy_sets_source_and_intake_type():
    staff = UserFactory(is_staff=True)

    toy = services.intake_purchased_toy(
        model_name="Train Set",
        make="Acme",
        condition=Toy.Condition.NEW,
        staff_user=staff,
    )

    assert toy.source == Toy.Source.PURCHASED
    assert toy.status == Toy.Status.AVAILABLE
    record = IntakeRecord.objects.get(toy=toy)
    assert record.intake_type == IntakeRecord.IntakeType.INITIAL_PURCHASE


@pytest.mark.django_db
def test_intake_toy_treats_blank_barcode_as_null():
    staff = UserFactory(is_staff=True)

    first = services.intake_purchased_toy(
        model_name="Item A", make="Acme", condition=Toy.Condition.NEW, staff_user=staff, barcode_or_sku=""
    )
    second = services.intake_purchased_toy(
        model_name="Item B", make="Acme", condition=Toy.Condition.NEW, staff_user=staff, barcode_or_sku=""
    )

    assert first.barcode_or_sku is None
    assert second.barcode_or_sku is None
