import pytest

from apps.common.factories import ToyFactory

from .models import Toy


@pytest.mark.django_db
class TestToyList:
    def test_requires_authentication(self, api_client):
        res = api_client.get("/api/toys/")
        assert res.status_code == 401

    def test_authenticated_member_can_list(self, member_client, toy):
        res = member_client.get("/api/toys/")
        assert res.status_code == 200
        assert len(res.data["results"]) == 1

    def test_status_filter(self, member_client):
        ToyFactory(status=Toy.Status.AVAILABLE)
        ToyFactory(status=Toy.Status.BROKEN)

        res = member_client.get("/api/toys/?status=AVAILABLE")

        assert res.status_code == 200
        assert all(t["status"] == "AVAILABLE" for t in res.data["results"])

    def test_search_filter(self, member_client):
        ToyFactory(model_name="Wooden Train", make="Acme")
        ToyFactory(model_name="Puzzle Cube", make="Other")

        res = member_client.get("/api/toys/?search=Train")

        assert res.status_code == 200
        assert len(res.data["results"]) == 1
        assert res.data["results"][0]["model_name"] == "Wooden Train"


@pytest.mark.django_db
class TestToyCreate:
    def test_member_cannot_create_toy(self, member_client):
        res = member_client.post("/api/toys/", {"model_name": "New Toy", "make": "Acme"})
        assert res.status_code == 403

    def test_staff_can_create_toy_starting_in_intake(self, staff_client):
        res = staff_client.post("/api/toys/", {"model_name": "New Toy", "make": "Acme"})

        assert res.status_code == 201
        assert res.data["status"] == "INTAKE"

    def test_status_field_is_read_only_on_create(self, staff_client):
        res = staff_client.post(
            "/api/toys/", {"model_name": "New Toy", "make": "Acme", "status": "AVAILABLE"}
        )

        assert res.status_code == 201
        assert res.data["status"] == "INTAKE"


@pytest.mark.django_db
class TestToyTransition:
    def test_staff_can_transition_toy(self, staff_client):
        toy = ToyFactory(status=Toy.Status.INTAKE)

        res = staff_client.post(
            f"/api/toys/{toy.id}/transition/", {"new_status": "AVAILABLE", "reason": "Stocked"}
        )

        assert res.status_code == 200
        assert res.data["status"] == "AVAILABLE"

    def test_illegal_transition_returns_400(self, staff_client):
        toy = ToyFactory(status=Toy.Status.RETIRED)

        res = staff_client.post(f"/api/toys/{toy.id}/transition/", {"new_status": "AVAILABLE"})

        assert res.status_code == 400

    def test_member_cannot_transition_toy(self, member_client, toy):
        res = member_client.post(f"/api/toys/{toy.id}/transition/", {"new_status": "BROKEN"})
        assert res.status_code == 403

    def test_status_log_records_transition(self, staff_client):
        toy = ToyFactory(status=Toy.Status.INTAKE)
        staff_client.post(f"/api/toys/{toy.id}/transition/", {"new_status": "AVAILABLE", "reason": "x"})

        res = staff_client.get(f"/api/toys/{toy.id}/status-log/")

        assert res.status_code == 200
        assert len(res.data) == 1
        assert res.data[0]["from_status"] == "INTAKE"
        assert res.data[0]["to_status"] == "AVAILABLE"


@pytest.mark.django_db
class TestToyStructuredFilters:
    def test_model_name_partial_match(self, member_client):
        ToyFactory(model_name="Wooden Train Set")
        ToyFactory(model_name="Puzzle Cube")

        res = member_client.get("/api/toys/?model_name=train")

        assert res.status_code == 200
        assert len(res.data["results"]) == 1
        assert res.data["results"][0]["model_name"] == "Wooden Train Set"

    def test_make_partial_match(self, member_client):
        ToyFactory(make="Fisher-Price")
        ToyFactory(make="Melissa & Doug")

        res = member_client.get("/api/toys/?make=fisher")

        assert res.status_code == 200
        assert len(res.data["results"]) == 1

    def test_age_filter_includes_toys_at_or_below_requested_age(self, member_client):
        ToyFactory(min_age_years=3)
        ToyFactory(min_age_years=5)

        res = member_client.get("/api/toys/?age=3")

        assert res.status_code == 200
        ages = {t["min_age_years"] for t in res.data["results"]}
        assert ages == {3}

    def test_age_filter_always_includes_toys_with_no_min_age(self, member_client):
        ToyFactory(min_age_years=None)
        ToyFactory(min_age_years=10)

        res = member_client.get("/api/toys/?age=1")

        assert res.status_code == 200
        assert len(res.data["results"]) == 1
        assert res.data["results"][0]["min_age_years"] is None

    def test_age_filter_rejects_non_numeric_value(self, member_client):
        res = member_client.get("/api/toys/?age=notanumber")
        assert res.status_code == 400

    def test_combining_make_model_name_and_age(self, member_client):
        ToyFactory(make="Acme", model_name="Wooden Blocks", min_age_years=2)
        ToyFactory(make="Acme", model_name="Wooden Blocks", min_age_years=8)
        ToyFactory(make="Other", model_name="Wooden Blocks", min_age_years=2)

        res = member_client.get("/api/toys/?make=acme&model_name=wooden&age=3")

        assert res.status_code == 200
        assert len(res.data["results"]) == 1


@pytest.mark.django_db
class TestToyGroups:
    def test_groups_by_make_and_model_name_with_counts(self, member_client):
        ToyFactory(make="Acme", model_name="Blocks", status=Toy.Status.AVAILABLE)
        ToyFactory(make="Acme", model_name="Blocks", status=Toy.Status.CHECKED_OUT)
        ToyFactory(make="Acme", model_name="Puzzle", status=Toy.Status.AVAILABLE)

        res = member_client.get("/api/toys/groups/")

        assert res.status_code == 200
        by_model = {g["model_name"]: g for g in res.data}
        assert by_model["Blocks"]["total_count"] == 2
        assert by_model["Blocks"]["available_count"] == 1
        assert by_model["Puzzle"]["total_count"] == 1
        assert by_model["Puzzle"]["available_count"] == 1

    def test_groups_endpoint_is_not_paginated(self, member_client):
        for i in range(30):
            ToyFactory(make="Acme", model_name=f"Model {i}")

        res = member_client.get("/api/toys/groups/")

        assert res.status_code == 200
        assert isinstance(res.data, list)
        assert len(res.data) == 30

    def test_groups_respects_filters(self, member_client):
        ToyFactory(make="Acme", model_name="Blocks", status=Toy.Status.AVAILABLE)
        ToyFactory(make="Other", model_name="Blocks", status=Toy.Status.AVAILABLE)

        res = member_client.get("/api/toys/groups/?make=acme")

        assert res.status_code == 200
        assert len(res.data) == 1
        assert res.data[0]["make"] == "Acme"

    def test_groups_respects_search_backend_too(self, member_client):
        ToyFactory(make="Acme", model_name="Wooden Train")
        ToyFactory(make="Acme", model_name="Puzzle Cube")

        res = member_client.get("/api/toys/groups/?search=Train")

        assert res.status_code == 200
        assert len(res.data) == 1
        assert res.data[0]["model_name"] == "Wooden Train"

    def test_groups_requires_authentication(self, api_client):
        res = api_client.get("/api/toys/groups/")
        assert res.status_code == 401
