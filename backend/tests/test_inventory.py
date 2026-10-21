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