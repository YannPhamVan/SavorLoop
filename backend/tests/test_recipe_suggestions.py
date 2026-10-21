from collections.abc import Iterator
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app import main
from backend.app.database import create_database_engine
from backend.app.gemini_recipes import DEFAULT_GEMINI_MODEL, GeminiRecipeProvider
from backend.app.models import Ingredient
from backend.app.recipe_suggestions import (
    RecipeAPIKeyMissing,
    RecipeModelOutput,
    RecipeProviderUnavailable,
    RecipeQuotaExhausted,
    RecipeStockItem,
    RecipeSuggestionService,
    select_recipe_context,
)


@pytest.fixture
def client(tmp_path, monkeypatch) -> Iterator[TestClient]:
    test_engine = create_database_engine(f"sqlite:///{tmp_path / 'recipes.db'}")
    monkeypatch.setattr(main, "engine", test_engine)
    try:
        with TestClient(main.app) as test_client:
            yield test_client
    finally:
        main.app.dependency_overrides.clear()
        test_engine.dispose()


def add_stock(client: TestClient) -> None:
    for payload in (
        {
            "category": "rotating",
            "name": "Spinach",
            "quantity": 500,
            "unit": "g",
            "expiry_date": "2026-10-25",
        },
        {"category": "rotating", "name": "Rice", "quantity": 1000, "unit": "g"},
        {"category": "pantry_staple", "name": "Olive oil", "available": True},
        {"category": "pantry_staple", "name": "Unavailable beans", "available": False},
    ):
        assert client.post("/api/inventory", json=payload).status_code == 201


def valid_recipe(**changes: object) -> dict:
    recipe = {
        "title": "Spinach rice bowl",
        "ingredients": [
            {"name": "Spinach", "quantity": 100, "unit": "g"},
            {"name": "Rice", "quantity": 150, "unit": "g"},
            {"name": "Olive oil", "quantity": 1, "unit": "tbsp"},
            {"name": "Lemon", "quantity": 0.5, "unit": "piece"},
        ],
        "steps": ["Cook the rice until tender.", "Wilt the spinach and serve over rice."],
        "preparation_time_minutes": 25,
        "substitutions": ["Use lime instead of lemon."],
    }
    recipe.update(changes)
    return recipe


class StubRecipeProvider:
    def __init__(self, *responses: object) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[list[RecipeStockItem], int, str | None]] = []

    def generate(
        self,
        stock: list[RecipeStockItem],
        requested_servings: int,
        correction: str | None = None,
    ) -> object:
        self.calls.append((stock, requested_servings, correction))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def set_provider(client: TestClient, provider: StubRecipeProvider) -> None:
    client.app.dependency_overrides[main.get_recipe_suggester] = lambda: RecipeSuggestionService(provider)


def test_context_prioritizes_earlier_dates_then_undated_and_excludes_unavailable() -> None:
    inventory = [
        Ingredient(category="rotating", name="Undated", quantity=2, unit="pcs"),
        Ingredient(category="pantry_staple", name="Unavailable", available=False),
        Ingredient(category="rotating", name="Later", quantity=2, unit="pcs", expiry_date=date(2026, 11, 3)),
        Ingredient(category="pantry_staple", name="Available pantry", available=True),
        Ingredient(category="rotating", name="Soon", quantity=2, unit="pcs", expiry_date=date(2026, 10, 24)),
    ]

    selected = select_recipe_context(inventory)

    assert [item.name for item in selected] == ["Soon", "Later", "Available pantry", "Undated"]


def test_suggestion_validates_fields_classifies_missing_and_scales_quantities(client: TestClient) -> None:
    add_stock(client)
    provider = StubRecipeProvider(valid_recipe())
    set_provider(client, provider)

    response = client.post("/api/suggestions", json={"servings": 4})

    assert response.status_code == 200
    result = response.json()
    assert result["servings"] == 4
    assert result["preparation_time_minutes"] == 25
    assert result["steps"] == ["Cook the rice until tender.", "Wilt the spinach and serve over rice."]
    assert result["substitutions"] == ["Use lime instead of lemon."]
    assert [item["name"] for item in result["missing_ingredients"]] == ["Lemon"]
    assert result["ingredients"][0]["quantity"] == 200
    assert result["ingredients"][1]["quantity"] == 300
    assert result["missing_ingredients"][0]["quantity"] == 1
    assert "Spinach" in result["stock_explanation"]
    assert "2026-10-25" in result["stock_explanation"]
    assert len(provider.calls) == 1
    assert [item.name for item in provider.calls[0][0]] == ["Spinach", "Olive oil", "Rice"]
    with Session(main.engine) as session:
        assert session.scalar(select(func.count()).select_from(Ingredient)) == 4
        assert session.scalar(select(Ingredient.quantity).where(Ingredient.name == "Spinach")) == 500


def test_two_missing_ingredients_are_allowed_but_three_trigger_one_retry(client: TestClient) -> None:
    add_stock(client)
    invalid = valid_recipe(
        ingredients=valid_recipe()["ingredients"]
        + [
            {"name": "Pepper", "quantity": 1, "unit": "pinch"},
            {"name": "Cheese", "quantity": 20, "unit": "g"},
        ]
    )
    provider = StubRecipeProvider(invalid, valid_recipe())
    set_provider(client, provider)

    response = client.post("/api/suggestions", json={"servings": 2})

    assert response.status_code == 200
    assert len(response.json()["missing_ingredients"]) == 1
    assert len(provider.calls) == 2
    assert provider.calls[0][2] is None
    assert provider.calls[1][2]


def test_invalid_structured_output_is_retried_once(client: TestClient) -> None:
    add_stock(client)
    provider = StubRecipeProvider({"title": "Not complete"}, valid_recipe())
    set_provider(client, provider)

    response = client.post("/api/suggestions", json={"servings": 2})

    assert response.status_code == 200
    assert len(provider.calls) == 2
    assert provider.calls[1][2]


def test_repeated_invalid_output_is_reported_and_never_persisted(client: TestClient) -> None:
    add_stock(client)
    provider = StubRecipeProvider({"title": "bad"}, {"title": "still bad"})
    set_provider(client, provider)

    response = client.post("/api/suggestions", json={"servings": 2})

    assert response.status_code == 502
    assert "one correction attempt" in response.json()["detail"]
    assert "No suggestion was saved" in response.json()["detail"]
    assert len(provider.calls) == 2
    with Session(main.engine) as session:
        assert session.scalar(select(func.count()).select_from(Ingredient)) == 4


@pytest.mark.parametrize("servings", [0, 13])
def test_servings_out_of_range_are_rejected(client: TestClient, servings: int) -> None:
    response = client.post("/api/suggestions", json={"servings": servings})

    assert response.status_code == 422


def test_scaled_amount_cannot_exceed_rotating_stock_and_can_be_corrected(client: TestClient) -> None:
    client.post(
        "/api/inventory",
        json={"category": "rotating", "name": "Spinach", "quantity": 150, "unit": "g"},
    )
    too_much = valid_recipe(ingredients=[{"name": "Spinach", "quantity": 100, "unit": "g"}])
    corrected = valid_recipe(ingredients=[{"name": "Spinach", "quantity": 70, "unit": "g"}])
    provider = StubRecipeProvider(too_much, corrected)
    set_provider(client, provider)

    response = client.post("/api/suggestions", json={"servings": 4})

    assert response.status_code == 200
    assert response.json()["ingredients"][0]["quantity"] == 140
    assert len(provider.calls) == 2


def test_missing_key_and_provider_errors_are_safe(client: TestClient, monkeypatch) -> None:
    add_stock(client)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    client.app.dependency_overrides[main.get_recipe_suggester] = lambda: RecipeSuggestionService(
        GeminiRecipeProvider()
    )

    missing_key = client.post("/api/suggestions", json={"servings": 2})
    assert missing_key.status_code == 503
    assert "GEMINI_API_KEY" in missing_key.json()["detail"]

    provider = StubRecipeProvider(RuntimeError("private provider diagnostic"))
    set_provider(client, provider)
    unavailable = client.post("/api/suggestions", json={"servings": 2})
    assert unavailable.status_code == 503
    assert "private" not in unavailable.text
    assert "diagnostic" not in unavailable.text


def test_quota_exhaustion_is_actionable_without_retry(client: TestClient) -> None:
    add_stock(client)
    provider = StubRecipeProvider(RecipeQuotaExhausted())
    set_provider(client, provider)

    response = client.post("/api/suggestions", json={"servings": 2})

    assert response.status_code == 429
    assert "quota" in response.json()["detail"].lower()
    assert len(provider.calls) == 1


def test_provider_uses_configured_model_and_disables_storage(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_MODEL", "gemini-test-model")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-a-real-secret")
    captured: dict = {}

    class Interactions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return type("Response", (), {"output_text": valid_recipe()})()

    class Client:
        def __init__(self, *, api_key: str) -> None:
            assert api_key == "test-key-not-a-real-secret"
            self.interactions = Interactions()

    monkeypatch.setattr("backend.app.gemini_recipes.genai.Client", Client)
    provider = GeminiRecipeProvider()
    stock = [
        RecipeStockItem(
            name="Spinach",
            category="rotating",
            quantity=500,
            unit="g",
            expiry_date=date(2026, 10, 25),
        )
    ]

    assert provider.model == "gemini-test-model"
    assert provider.generate(stock, 4) == valid_recipe()
    assert captured["model"] == "gemini-test-model"
    assert captured["store"] is False
    assert captured["generation_config"] == {"thinking_level": "low", "max_output_tokens": 1200}
    assert captured["response_format"]["mime_type"] == "application/json"


def test_provider_defaults_to_current_free_tier_model(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_MODEL", raising=False)

    assert GeminiRecipeProvider().model == DEFAULT_GEMINI_MODEL