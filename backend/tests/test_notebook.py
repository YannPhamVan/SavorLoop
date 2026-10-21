from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app import main
from backend.app.database import create_database_engine
from backend.app.models import CookingAttempt, NotebookRecipe
from backend.app.recipe_suggestions import RecipeFeedbackContext, RecipeStockItem, RecipeSuggestionService


@pytest.fixture
def client(tmp_path, monkeypatch) -> Iterator[TestClient]:
    test_engine = create_database_engine(f"sqlite:///{tmp_path / 'notebook.db'}")
    monkeypatch.setattr(main, "engine", test_engine)
    try:
        with TestClient(main.app) as test_client:
            yield test_client
    finally:
        main.app.dependency_overrides.clear()
        test_engine.dispose()


def suggestion(**changes: object) -> dict:
    recipe = {
        "title": "Spinach rice bowl",
        "ingredients": [{"name": "Spinach", "quantity": 100, "unit": "g"}],
        "steps": ["Cook the rice.", "Wilt the spinach and serve."],
        "preparation_time_minutes": 20,
        "substitutions": ["Use lime instead of lemon."],
        "servings": 2,
        "missing_ingredients": [],
        "stock_explanation": "Built around available stock, including Spinach.",
    }
    recipe.update(changes)
    return recipe


def attempt(
    rating: int,
    attempt_date: str,
    *,
    comments: str = "",
    changes: list[str] | None = None,
    substitutions: list[str] | None = None,
    liked_adjustments: list[str] | None = None,
) -> dict:
    return {
        "attempt_date": attempt_date,
        "rating": rating,
        "comments": comments,
        "changes": changes or [],
        "substitutions": substitutions or [],
        "liked_adjustments": liked_adjustments or [],
    }


class StubRecipeProvider:
    def __init__(self) -> None:
        self.feedback: list[RecipeFeedbackContext] | None = None

    def generate(
        self,
        stock: list[RecipeStockItem],
        requested_servings: int,
        correction: str | None = None,
        feedback_context: list[RecipeFeedbackContext] | None = None,
    ) -> object:
        self.feedback = feedback_context or []
        return {
            "title": "Spinach rice bowl",
            "ingredients": [{"name": "Spinach", "quantity": 100, "unit": "g"}],
            "steps": ["Cook the rice.", "Wilt the spinach and serve."],
            "preparation_time_minutes": 20,
            "substitutions": [],
        }


def set_provider(client: TestClient, provider: StubRecipeProvider) -> None:
    client.app.dependency_overrides[main.get_recipe_suggester] = lambda: RecipeSuggestionService(provider)

def assert_notebook_counts(recipe_count: int, attempt_count: int) -> None:
    with Session(main.engine) as session:
        assert session.scalar(select(func.count()).select_from(NotebookRecipe)) == recipe_count
        assert session.scalar(select(func.count()).select_from(CookingAttempt)) == attempt_count


def create_notebook_recipe(
    client: TestClient,
    title: str,
    first_attempt: dict,
) -> dict:
    response = client.post(
        "/api/notebook",
        json={"recipe": suggestion(title=title), "attempt": first_attempt},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_suggestion_is_transient_until_cooked_confirmation(client: TestClient) -> None:
    client.post(
        "/api/inventory",
        json={"category": "rotating", "name": "Spinach", "quantity": 500, "unit": "g"},
    )
    provider = StubRecipeProvider()
    set_provider(client, provider)

    generated = client.post("/api/suggestions", json={"servings": 2})

    assert generated.status_code == 200
    assert "id" not in generated.json()
    assert client.get("/api/notebook").json() == []
    assert provider.feedback == []
    assert_notebook_counts(0, 0)

    invalid_confirmation = client.post(
        "/api/notebook",
        json={"recipe": suggestion(), "attempt": attempt(6, "2026-10-21")},
    )
    invalid_likes = client.post(
        "/api/notebook",
        json={
            "recipe": suggestion(),
            "attempt": attempt(5, "2026-10-21", liked_adjustments=["unrecorded preference"]),
        },
    )
    assert invalid_confirmation.status_code == 422
    assert invalid_likes.status_code == 422
    assert_notebook_counts(0, 0)

    confirmed = client.post(
        "/api/notebook",
        json={
            "recipe": suggestion(),
            "attempt": attempt(
                5,
                "2026-10-21",
                comments="Bright and quick.",
                changes=["extra lemon"],
                substitutions=["lime for lemon"],
                liked_adjustments=["extra lemon"],
            ),
        },
    )

    assert confirmed.status_code == 201
    assert confirmed.json()["recipe"] == suggestion()
    assert_notebook_counts(1, 1)
    assert confirmed.json()["attempts"][0]["liked_adjustments"] == ["extra lemon"]
    assert len(client.get("/api/notebook").json()) == 1


def test_attempts_append_and_invalid_attempts_do_not_mutate_history(client: TestClient) -> None:
    created = create_notebook_recipe(client, "Spinach rice bowl", attempt(4, "2026-10-20"))

    invalid = client.post(
        f"/api/notebook/{created['id']}/attempts",
        json=attempt(6, "2026-10-21"),
    )
    invalid_like = client.post(
        f"/api/notebook/{created['id']}/attempts",
        json=attempt(5, "2026-10-21", comments="loved the spice", liked_adjustments=["more spice"]),
    )
    assert invalid.status_code == 422
    assert invalid_like.status_code == 422
    assert_notebook_counts(1, 1)

    appended = client.post(
        f"/api/notebook/{created['id']}/attempts",
        json=attempt(
            5,
            "2026-10-21",
            comments="Better with the extra lemon.",
            changes=["extra lemon"],
            substitutions=["lime for lemon"],
            liked_adjustments=["extra lemon"],
        ),
    )

    assert appended.status_code == 201
    history = client.get("/api/notebook").json()[0]["attempts"]
    assert len(history) == 2
    assert [entry["rating"] for entry in history] == [4, 5]
    assert history[0]["attempt_date"] == "2026-10-20"
    assert history[0]["comments"] == ""
    assert history[1]["liked_adjustments"] == ["extra lemon"]
    assert history[1]["comments"] == "Better with the extra lemon."
    assert history[1]["substitutions"] == ["lime for lemon"]
    assert_notebook_counts(1, 2)


def test_feedback_selection_uses_latest_ratings_order_and_explicit_likes(client: TestClient) -> None:
    alpha = create_notebook_recipe(
        client,
        "Alpha",
        attempt(5, "2026-10-19", changes=["old adjustment"], liked_adjustments=["old adjustment"]),
    )
    client.post(
        f"/api/notebook/{alpha['id']}/attempts",
        json=attempt(
            5,
            "2026-10-20",
            changes=["extra lemon"],
            substitutions=["lime for lemon"],
            liked_adjustments=["extra lemon", "lime for lemon"],
        ),
    )
    create_notebook_recipe(client, "Beta", attempt(5, "2026-10-20"))
    create_notebook_recipe(client, "Gamma", attempt(5, "2026-10-19"))
    create_notebook_recipe(client, "Delta", attempt(4, "2026-10-22"))
    later_low = create_notebook_recipe(client, "Later low", attempt(5, "2026-10-18"))
    client.post(
        f"/api/notebook/{later_low['id']}/attempts",
        json=attempt(3, "2026-10-23", changes=["more salt"], liked_adjustments=["more salt"]),
    )
    client.post(
        "/api/inventory",
        json={"category": "rotating", "name": "Spinach", "quantity": 500, "unit": "g"},
    )
    provider = StubRecipeProvider()
    set_provider(client, provider)

    response = client.post("/api/suggestions", json={"servings": 2})

    assert response.status_code == 200
    assert provider.feedback is not None
    assert [entry.recipe.title for entry in provider.feedback] == ["Alpha", "Beta", "Gamma"]
    assert provider.feedback[0].liked_adjustments == ["extra lemon", "lime for lemon"]
    assert provider.feedback[1].liked_adjustments == []
    assert all(entry.recipe.title != "Delta" for entry in provider.feedback)
    assert all(entry.recipe.title != "Later low" for entry in provider.feedback)
    with Session(main.engine) as session:
        assert session.scalar(select(func.count()).select_from(NotebookRecipe)) == 5