from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app import main
from backend.app.models import Ingredient
from backend.app.database import create_database_engine


@pytest.fixture
def client(tmp_path, monkeypatch) -> Iterator[TestClient]:
    test_engine = create_database_engine(f"sqlite:///{tmp_path / 'inventory.db'}")
    monkeypatch.setattr(main, "engine", test_engine)
    try:
        with TestClient(main.app) as test_client:
            yield test_client
    finally:
        main.app.dependency_overrides.clear()
        test_engine.dispose()


def stored_ingredients() -> list[Ingredient]:
    with Session(main.engine) as session:
        return list(session.scalars(select(Ingredient).order_by(Ingredient.id)))


def test_pantry_staple_crud(client: TestClient) -> None:
    created = client.post(
        "/api/inventory",
        json={"category": "pantry_staple", "name": "  Olive oil  ", "available": True},
    )
    assert created.status_code == 201
    ingredient = created.json()
    assert ingredient["name"] == "Olive oil"
    assert ingredient["available"] is True
    assert ingredient["quantity"] is None

    listed = client.get("/api/inventory")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [ingredient["id"]]

    updated = client.put(
        f"/api/inventory/{ingredient['id']}",
        json={"category": "pantry_staple", "name": "Olive oil", "available": False},
    )
    assert updated.status_code == 200
    assert updated.json()["available"] is False

    deleted = client.delete(f"/api/inventory/{ingredient['id']}")
    assert deleted.status_code == 204
    assert client.get("/api/inventory").json() == []


def test_rotating_ingredient_crud(client: TestClient) -> None:
    created = client.post(
        "/api/inventory",
        json={
            "category": "rotating",
            "name": "Mushrooms",
            "quantity": 250,
            "unit": "g",
            "expiry_date": "2026-10-28",
        },
    )
    assert created.status_code == 201
    ingredient = created.json()
    assert ingredient["quantity"] == 250
    assert ingredient["expiry_date"] == "2026-10-28"

    updated = client.put(
        f"/api/inventory/{ingredient['id']}",
        json={"category": "rotating", "name": "Cremini mushrooms", "quantity": 0.5, "unit": "kg"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Cremini mushrooms"
    assert updated.json()["expiry_date"] is None

    deleted = client.delete(f"/api/inventory/{ingredient['id']}")
    assert deleted.status_code == 204
    assert client.get("/api/inventory").json() == []


@pytest.mark.parametrize(
    "payload",
    [
        {"category": "pantry_staple", "name": "Rice", "available": True, "quantity": 1},
        {"category": "rotating", "name": "Rice", "quantity": 1},
        {"category": "rotating", "name": "Rice", "quantity": 1, "unit": " "},
        {"category": "rotating", "name": "Rice", "quantity": 0, "unit": "kg"},
        {"category": "rotating", "name": "Rice", "quantity": -1, "unit": "kg"},
        {"category": "rotating", "name": "Rice", "quantity": 1, "unit": "kg", "expiry_date": "2026-02-30"},
    ],
)
def test_invalid_create_is_rejected_without_mutation(client: TestClient, payload: dict) -> None:
    response = client.post("/api/inventory", json=payload)

    assert response.status_code == 422
    with Session(main.engine) as session:
        assert session.scalar(select(func.count()).select_from(Ingredient)) == 0


def test_non_finite_create_is_rejected_without_mutation(client: TestClient) -> None:
    response = client.post(
        "/api/inventory",
        content='{"category":"rotating","name":"Rice","quantity":1e309,"unit":"kg"}',
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 422
    assert stored_ingredients() == []


def test_invalid_update_is_rejected_without_mutation(client: TestClient) -> None:
    created = client.post(
        "/api/inventory",
        json={"category": "rotating", "name": "Mushrooms", "quantity": 250, "unit": "g"},
    )
    ingredient_id = created.json()["id"]

    response = client.put(
        f"/api/inventory/{ingredient_id}",
        json={
            "category": "rotating",
            "name": "Changed mushrooms",
            "quantity": 0,
            "unit": "g",
        },
    )

    assert response.status_code == 422
    ingredient = stored_ingredients()[0]
    assert (ingredient.name, ingredient.quantity, ingredient.unit) == ("Mushrooms", 250, "g")


def test_pantry_staple_rejects_rotating_fields_on_update_without_mutation(client: TestClient) -> None:
    created = client.post(
        "/api/inventory",
        json={"category": "pantry_staple", "name": "Olive oil", "available": True},
    )
    ingredient_id = created.json()["id"]

    response = client.put(
        f"/api/inventory/{ingredient_id}",
        json={
            "category": "pantry_staple",
            "name": "Changed olive oil",
            "available": False,
            "expiry_date": None,
        },
    )

    assert response.status_code == 422
    ingredient = stored_ingredients()[0]
    assert (ingredient.name, ingredient.available) == ("Olive oil", True)


class StubInventoryInterpreter:
    def __init__(self, *responses: object) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[str, str | None]] = []

    def interpret(self, text: str, correction: str | None = None) -> object:
        self.calls.append((text, correction))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def set_interpreter(client: TestClient, interpreter: StubInventoryInterpreter) -> None:
    client.app.dependency_overrides[main.get_inventory_interpreter] = lambda: interpreter


def add_natural_language_fixtures(client: TestClient) -> None:
    client.post(
        "/api/inventory",
        json={"category": "pantry_staple", "name": "Olive oil", "available": True},
    )
    client.post(
        "/api/inventory",
        json={"category": "rotating", "name": "Mushrooms", "quantity": 250, "unit": "g"},
    )


@pytest.mark.parametrize(
    ("operation", "expected_detail"),
    [
        ({"action": "consume", "ingredient": "Unknown", "amount": 10, "unit": "g"}, "No inventory item matches"),
        ({"action": "consume", "ingredient": "Mushrooms", "amount": 10, "unit": "kg"}, "requested unit does not match"),
        ({"action": "consume", "ingredient": "Mushrooms", "amount": -10, "unit": "g"}, "couldn't safely interpret"),
        ({"action": "consume", "ingredient": "Mushrooms", "amount": 300, "unit": "g"}, "exceeds the usable recorded stock"),
    ],
)
def test_invalid_natural_language_update_does_not_mutate_inventory(
    client: TestClient,
    operation: dict,
    expected_detail: str,
) -> None:
    add_natural_language_fixtures(client)
    interpreter = StubInventoryInterpreter({"operations": [operation]}, {"operations": [operation]})
    set_interpreter(client, interpreter)

    response = client.post("/api/inventory/natural-language", json={"text": "update stock"})

    assert response.status_code == 422
    assert expected_detail in response.json()["detail"]
    assert len(interpreter.calls) == 2
    assert [(item.available, item.quantity) for item in stored_ingredients()] == [(True, None), (None, 250)]


def test_natural_language_update_applies_valid_operations_atomically(client: TestClient) -> None:
    add_natural_language_fixtures(client)
    interpreter = StubInventoryInterpreter(
        {
            "operations": [
                {"action": "set_unavailable", "ingredient": " olive OIL "},
                {"action": "consume", "ingredient": "Mushrooms", "amount": 50, "unit": " G "},
            ]
        }
    )
    set_interpreter(client, interpreter)

    response = client.post(
        "/api/inventory/natural-language",
        json={"text": "Mark olive oil unavailable and use 50 g mushrooms"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "updated", "message": "Inventory updated.", "updated_count": 2}
    assert len(interpreter.calls) == 1
    assert [(item.available, item.quantity) for item in stored_ingredients()] == [(False, None), (None, 200)]


def test_invalid_structured_output_is_corrected_once_then_applied(client: TestClient) -> None:
    add_natural_language_fixtures(client)
    interpreter = StubInventoryInterpreter(
        {"operations": [{"action": "consume", "ingredient": "Mushrooms", "amount": -1, "unit": "g"}]},
        {"operations": [{"action": "consume", "ingredient": "Mushrooms", "amount": 25, "unit": "g"}]},
    )
    set_interpreter(client, interpreter)

    response = client.post("/api/inventory/natural-language", json={"text": "use mushrooms"})

    assert response.status_code == 200
    assert len(interpreter.calls) == 2
    assert interpreter.calls[0] == ("use mushrooms", None)
    assert interpreter.calls[1][0] == "use mushrooms"
    assert interpreter.calls[1][1]
    assert stored_ingredients()[1].quantity == 225


def test_repeated_invalid_structured_output_has_no_partial_write(client: TestClient) -> None:
    add_natural_language_fixtures(client)
    interpreter = StubInventoryInterpreter(
        {
            "operations": [
                {"action": "set_unavailable", "ingredient": "Olive oil"},
                {"action": "consume", "ingredient": "Mushrooms", "amount": -2, "unit": "g"},
            ]
        },
        {
            "operations": [
                {"action": "set_unavailable", "ingredient": "Olive oil"},
                {"action": "consume", "ingredient": "Mushrooms", "amount": -2, "unit": "g"},
            ]
        },
    )
    set_interpreter(client, interpreter)

    response = client.post("/api/inventory/natural-language", json={"text": "update both items"})

    assert response.status_code == 422
    assert len(interpreter.calls) == 2
    assert [(item.available, item.quantity) for item in stored_ingredients()] == [(True, None), (None, 250)]


def test_unconfigured_interpreter_fails_safely_without_mutation(client: TestClient) -> None:
    add_natural_language_fixtures(client)

    response = client.post("/api/inventory/natural-language", json={"text": "use some mushrooms"})

    assert response.status_code == 503
    assert "inventory controls" in response.json()["detail"]
    assert [(item.available, item.quantity) for item in stored_ingredients()] == [(True, None), (None, 250)]


def test_provider_diagnostics_are_not_exposed_to_the_user(client: TestClient) -> None:
    add_natural_language_fixtures(client)
    interpreter = StubInventoryInterpreter(RuntimeError("provider credential diagnostic"))
    set_interpreter(client, interpreter)

    response = client.post("/api/inventory/natural-language", json={"text": "use some mushrooms"})

    assert response.status_code == 503
    assert "credential" not in response.text
    assert "diagnostic" not in response.text
    assert [(item.available, item.quantity) for item in stored_ingredients()] == [(True, None), (None, 250)]


def test_valid_operation_before_invalid_operation_is_atomic(client: TestClient) -> None:
    add_natural_language_fixtures(client)
    plan = {
        "operations": [
            {"action": "set_unavailable", "ingredient": "Olive oil"},
            {"action": "consume", "ingredient": "Mushrooms", "amount": 300, "unit": "g"},
        ]
    }
    interpreter = StubInventoryInterpreter(plan, plan)
    set_interpreter(client, interpreter)

    response = client.post("/api/inventory/natural-language", json={"text": "update both items"})

    assert response.status_code == 422
    assert len(interpreter.calls) == 2
    assert [(item.available, item.quantity) for item in stored_ingredients()] == [(True, None), (None, 250)]


def test_ambiguous_normalized_name_is_rejected_without_mutation(client: TestClient) -> None:
    add_natural_language_fixtures(client)
    client.post(
        "/api/inventory",
        json={"category": "pantry_staple", "name": "OLIVE   OIL", "available": True},
    )
    plan = {"operations": [{"action": "set_unavailable", "ingredient": "olive oil"}]}
    interpreter = StubInventoryInterpreter(plan, plan)
    set_interpreter(client, interpreter)

    response = client.post("/api/inventory/natural-language", json={"text": "mark olive oil unavailable"})

    assert response.status_code == 422
    assert "unambiguous name" in response.json()["detail"]
    assert [item.available for item in stored_ingredients() if item.category == "pantry_staple"] == [True, True]


@pytest.mark.parametrize(
    "operation",
    [
        {"action": "consume", "ingredient": "Olive oil", "amount": 1, "unit": "ml"},
        {"action": "set_unavailable", "ingredient": "Mushrooms"},
    ],
)
def test_category_incompatible_operation_is_rejected_without_mutation(
    client: TestClient,
    operation: dict,
) -> None:
    add_natural_language_fixtures(client)
    interpreter = StubInventoryInterpreter({"operations": [operation]}, {"operations": [operation]})
    set_interpreter(client, interpreter)

    response = client.post("/api/inventory/natural-language", json={"text": "change inventory"})

    assert response.status_code == 422
    assert [(item.available, item.quantity) for item in stored_ingredients()] == [(True, None), (None, 250)]