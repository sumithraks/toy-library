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


def test_identify_toy_from_image_requires_api_key(settings):
    from apps.inventory import vision

    settings.ANTHROPIC_API_KEY = ""

    with pytest.raises(ValueError, match="not configured"):
        vision.identify_toy_from_image(b"fake-image-bytes")


def test_identify_toy_from_image_returns_structured_result(settings):
    from unittest.mock import patch

    from apps.inventory import vision

    settings.ANTHROPIC_API_KEY = "test-key"

    expected = vision.ToyIdentification(
        model_name="Wooden Train Set",
        make="Acme",
        condition="LIGHTLY_USED",
        age_rating_label="3+",
        description="A wooden train set with tracks.",
    )
    with patch("apps.inventory.vision.ChatAnthropic") as mock_chat_cls:
        mock_structured_model = mock_chat_cls.return_value.with_structured_output.return_value
        mock_structured_model.invoke.return_value = expected

        result = vision.identify_toy_from_image(b"fake-image-bytes", mime_type="image/png")

    assert result == expected
    mock_chat_cls.return_value.with_structured_output.assert_called_once_with(
        vision.ToyIdentification
    )
    mock_structured_model.invoke.assert_called_once()


def test_identify_toy_from_image_logs_and_reraises_on_failure(settings):
    from unittest.mock import patch

    from apps.inventory import vision

    settings.ANTHROPIC_API_KEY = "test-key"

    with patch("apps.inventory.vision.ChatAnthropic") as mock_chat_cls, patch(
        "apps.inventory.vision.logger"
    ) as mock_logger:
        mock_structured_model = mock_chat_cls.return_value.with_structured_output.return_value
        mock_structured_model.invoke.side_effect = RuntimeError("upstream failure")

        with pytest.raises(RuntimeError, match="upstream failure"):
            vision.identify_toy_from_image(b"fake-image-bytes", mime_type="image/png")

    mock_logger.exception.assert_called_once_with("Toy image identification request failed")


@pytest.mark.django_db
def test_embed_toy_description_generates_and_saves_embedding():
    from unittest.mock import patch

    toy = ToyFactory(description="A wooden train set with tracks.")
    fake_vector = [0.1] * 1024

    with patch("apps.inventory.embeddings.embed_text", return_value=fake_vector) as mock_embed:
        services.embed_toy_description(toy)

    toy.refresh_from_db()
    assert list(toy.description_embedding) == fake_vector
    mock_embed.assert_called_once_with("A wooden train set with tracks.", input_type="document")


@pytest.mark.django_db
def test_embed_toy_description_skips_blank_description():
    from unittest.mock import patch

    toy = ToyFactory(description="")

    with patch("apps.inventory.embeddings.embed_text") as mock_embed:
        services.embed_toy_description(toy)

    mock_embed.assert_not_called()
    assert toy.description_embedding is None


@pytest.mark.django_db
def test_embed_toy_description_swallows_errors():
    from unittest.mock import patch

    toy = ToyFactory(description="A puzzle.")

    with patch("apps.inventory.embeddings.embed_text", side_effect=RuntimeError("upstream down")):
        services.embed_toy_description(toy)  # must not raise

    toy.refresh_from_db()
    assert toy.description_embedding is None


@pytest.mark.django_db
def test_intake_toy_generates_embedding_when_description_present():
    from unittest.mock import patch

    staff = UserFactory(is_staff=True)
    fake_vector = [0.2] * 1024

    with patch("apps.inventory.embeddings.embed_text", return_value=fake_vector):
        toy = services.intake_purchased_toy(
            model_name="Puzzle",
            make="Acme",
            condition=Toy.Condition.NEW,
            staff_user=staff,
            description="A 100-piece jigsaw puzzle of a mountain landscape.",
        )

    assert list(toy.description_embedding) == fake_vector


@pytest.mark.django_db
def test_backfill_toy_embeddings_only_fills_missing_by_default():
    from io import StringIO
    from unittest.mock import patch

    from django.core.management import call_command

    already_embedded = ToyFactory(description="a puzzle")
    already_embedded.description_embedding = [0.5] * 1024
    already_embedded.save(update_fields=["description_embedding"])
    missing = ToyFactory(description="a train set", description_embedding=None)
    no_description = ToyFactory(description="")

    with patch("apps.inventory.embeddings.embed_text", return_value=[0.7] * 1024) as mock_embed:
        call_command("backfill_toy_embeddings", stdout=StringIO())

    mock_embed.assert_called_once_with("a train set", input_type="document")
    missing.refresh_from_db()
    assert list(missing.description_embedding) == [0.7] * 1024
    no_description.refresh_from_db()
    assert no_description.description_embedding is None


@pytest.mark.django_db
def test_backfill_toy_embeddings_with_all_flag_regenerates_existing():
    from io import StringIO
    from unittest.mock import patch

    from django.core.management import call_command

    toy = ToyFactory(description="a puzzle")
    toy.description_embedding = [0.5] * 1024
    toy.save(update_fields=["description_embedding"])

    with patch("apps.inventory.embeddings.embed_text", return_value=[0.9] * 1024):
        call_command("backfill_toy_embeddings", "--all", stdout=StringIO())

    toy.refresh_from_db()
    assert list(toy.description_embedding) == [0.9] * 1024


def test_embed_text_requires_api_key(settings):
    from apps.inventory import embeddings

    settings.VOYAGE_API_KEY = ""

    with pytest.raises(ValueError, match="not configured"):
        embeddings.embed_text("a red toy car")


def test_embed_text_calls_voyage_client_with_configured_model(settings):
    from unittest.mock import patch

    from apps.inventory import embeddings

    settings.VOYAGE_API_KEY = "test-key"
    fake_vector = [0.4] * 1024

    with patch("apps.inventory.embeddings.voyageai.Client") as mock_client_cls:
        mock_client_cls.return_value.embed.return_value.embeddings = [fake_vector]

        result = embeddings.embed_text("a red toy car", input_type="query")

    assert result == fake_vector
    mock_client_cls.assert_called_once_with(api_key="test-key")
    mock_client_cls.return_value.embed.assert_called_once_with(
        ["a red toy car"], model=embeddings.EMBEDDING_MODEL, input_type="query"
    )
