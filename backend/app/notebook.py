from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.models import CookingAttempt, NotebookRecipe
from backend.app.recipe_suggestions import RecipeFeedbackContext, RecipeSuggestion


class CookingAttemptWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attempt_date: date
    rating: int = Field(ge=1, le=5)
    comments: str = Field(default="", max_length=2000)
    changes: list[str] = Field(default_factory=list, max_length=20)
    substitutions: list[str] = Field(default_factory=list, max_length=20)
    liked_adjustments: list[str] = Field(default_factory=list, max_length=40)

    @field_validator("comments")
    @classmethod
    def normalize_comments(cls, value: str) -> str:
        return value.strip()

    @field_validator("changes", "substitutions", "liked_adjustments")
    @classmethod
    def normalize_adjustments(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value or len(value) > 200 for value in normalized):
            raise ValueError("Adjustments must contain 1 to 200 characters")
        return normalized

    @model_validator(mode="after")
    def validate_liked_adjustments(self) -> "CookingAttemptWrite":
        available_adjustments = set(self.changes + self.substitutions)
        if len(self.liked_adjustments) != len(set(self.liked_adjustments)):
            raise ValueError("Liked adjustments cannot contain duplicates")
        if not set(self.liked_adjustments).issubset(available_adjustments):
            raise ValueError("Liked adjustments must be selected from changes or substitutions")
        return self


class NotebookRecipeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recipe: RecipeSuggestion
    attempt: CookingAttemptWrite


class CookingAttemptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    attempt_date: date
    rating: int
    comments: str
    changes: list[str]
    substitutions: list[str]
    liked_adjustments: list[str]


class NotebookRecipeRead(BaseModel):
    id: int
    recipe: RecipeSuggestion
    attempts: list[CookingAttemptRead]


def recipe_to_read(recipe: NotebookRecipe) -> NotebookRecipeRead:
    return NotebookRecipeRead(
        id=recipe.id,
        recipe=RecipeSuggestion.model_validate(recipe.snapshot),
        attempts=[CookingAttemptRead.model_validate(attempt) for attempt in recipe.attempts],
    )


def select_recipe_feedback(session: Session) -> list[RecipeFeedbackContext]:
    recipes = session.scalars(
        select(NotebookRecipe)
        .options(selectinload(NotebookRecipe.attempts))
        .order_by(NotebookRecipe.id)
    ).all()
    qualifying: list[tuple[int, date, int, RecipeFeedbackContext]] = []
    for recipe in recipes:
        if not recipe.attempts:
            continue
        latest_attempt = max(
            recipe.attempts,
            key=lambda attempt: (attempt.attempt_date, attempt.id),
        )
        if latest_attempt.rating < 4:
            continue
        qualifying.append(
            (
                latest_attempt.rating,
                latest_attempt.attempt_date,
                recipe.id,
                RecipeFeedbackContext(
                    recipe=RecipeSuggestion.model_validate(recipe.snapshot),
                    liked_adjustments=list(latest_attempt.liked_adjustments),
                ),
            )
        )

    qualifying.sort(key=lambda item: (-item[0], -item[1].toordinal(), item[2]))
    return [item[3] for item in qualifying[:3]]


def make_attempt(payload: CookingAttemptWrite) -> CookingAttempt:
    return CookingAttempt(**payload.model_dump())