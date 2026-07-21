import pytest

from apps.common.factories import ToyFactory, UserFactory
from apps.inventory import services
from apps.inventory.models import Toy, ToyStatusLog


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
