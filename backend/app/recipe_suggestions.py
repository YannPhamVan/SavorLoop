import json
import unicodedata
from collections.abc import Iterable
from datetime import date
from decimal import Decimal
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from backend.app.models import Ingredient

BASE_SERVINGS = 2
MAX_CONTEXT_ITEMS = 20


class RecipeSuggestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    servings: int = Field(ge=1, le=12)


class RecipeIngredient(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=120)
    quantity: float = Field(gt=0, allow_inf_nan=False)
    unit: str = Field(min_length=1, max_length=40)


class RecipeModelOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=120)
    ingredients: list[RecipeIngredient] = Field(min_length=1, max_length=20)
    steps: list[str] = Field(min_length=2, max_length=16)
    preparation_time_minutes: int = Field(ge=1, le=240)
    substitutions: list[str] = Field(max_length=8)

    @field_validator("steps", "substitutions")
    @classmethod
    def validate_text_items(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized):
            raise ValueError("Recipe text items cannot be empty")
        return normalized


class RecipeSuggestion(RecipeModelOutput):
    servings: int = Field(ge=1, le=12)
    missing_ingredients: list[RecipeIngredient] = Field(max_length=2)
    stock_explanation: str = Field(min_length=1, max_length=300)


class RecipeStockItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    category: str
    quantity: float | None
    unit: str | None
    expiry_date: date | None


class RecipeProvider(Protocol):
    def generate(
        self,
        stock: list[RecipeStockItem],
        requested_servings: int,
        correction: str | None = None,
    ) -> object: ...


class RecipeAPIKeyMissing(RuntimeError):
    pass


class RecipeQuotaExhausted(RuntimeError):
    pass


class RecipeProviderUnavailable(RuntimeError):
    pass


class RecipeInventoryUnavailable(ValueError):
    pass


class RecipeResponseInvalid(ValueError):
    pass


def _normalize(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).split()).casefold()


def select_recipe_context(inventory: Iterable[Ingredient]) -> list[RecipeStockItem]:
    available = [
        ingredient
        for ingredient in inventory
        if ingredient.category == "rotating" or ingredient.available is True
    ]
    available.sort(
        key=lambda ingredient: (
            ingredient.expiry_date is None,
            ingredient.expiry_date or date.max,
            _normalize(ingredient.name),
            ingredient.id or 0,
        )
    )
    return [
        RecipeStockItem(
            name=ingredient.name,
            category=ingredient.category,
            quantity=ingredient.quantity,
            unit=ingredient.unit,
            expiry_date=ingredient.expiry_date,
        )
        for ingredient in available[:MAX_CONTEXT_ITEMS]
    ]


def _parse_model_output(value: object) -> RecipeModelOutput:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            raise RecipeResponseInvalid from None
    try:
        return RecipeModelOutput.model_validate(value)
    except (ValidationError, TypeError, ValueError):
        raise RecipeResponseInvalid from None


def _scaled_quantity(quantity: float, servings: int) -> float:
    return float(Decimal(str(quantity)) * Decimal(servings) / Decimal(BASE_SERVINGS))


class RecipeSuggestionService:
    def __init__(self, provider: RecipeProvider) -> None:
        self.provider = provider

    def suggest(self, inventory: Iterable[Ingredient], servings: int) -> RecipeSuggestion:
        stock = select_recipe_context(inventory)
        if not stock:
            raise RecipeInventoryUnavailable

        correction: str | None = None
        for attempt in range(2):
            try:
                raw_output = self.provider.generate(stock, servings, correction)
            except (RecipeAPIKeyMissing, RecipeQuotaExhausted, RecipeProviderUnavailable):
                raise
            except Exception:
                raise RecipeProviderUnavailable from None
            try:
                recipe = _parse_model_output(raw_output)
                return self._validate_and_scale(recipe, stock, servings)
            except RecipeResponseInvalid:
                if attempt == 1:
                    raise RecipeResponseInvalid from None
                correction = (
                    "Return a complete valid recipe. Use exact available ingredient names and units, "
                    "keep scaled rotating quantities within stock, and include no more than two "
                    "ingredients that are not available."
                )
        raise RecipeResponseInvalid

    @staticmethod
    def _validate_and_scale(
        recipe: RecipeModelOutput,
        stock: list[RecipeStockItem],
        servings: int,
    ) -> RecipeSuggestion:
        stock_by_name = {_normalize(item.name): item for item in stock}
        recipe_names = [_normalize(item.name) for item in recipe.ingredients]
        if len(recipe_names) != len(set(recipe_names)):
            raise RecipeResponseInvalid

        matched_stock = [stock_by_name.get(name) for name in recipe_names]
        if not any(item is not None for item in matched_stock):
            raise RecipeResponseInvalid

        missing = [
            ingredient
            for ingredient, stock_item in zip(recipe.ingredients, matched_stock, strict=True)
            if stock_item is None
        ]
        if len(missing) > 2:
            raise RecipeResponseInvalid

        scaled_ingredients: list[RecipeIngredient] = []
        used_stock: list[RecipeStockItem] = []
        for ingredient, stock_item in zip(recipe.ingredients, matched_stock, strict=True):
            scaled_quantity = _scaled_quantity(ingredient.quantity, servings)
            if stock_item is not None:
                used_stock.append(stock_item)
                if stock_item.category == "rotating":
                    if _normalize(ingredient.unit) != _normalize(stock_item.unit or ""):
                        raise RecipeResponseInvalid
                    if scaled_quantity > (stock_item.quantity or 0):
                        raise RecipeResponseInvalid
            scaled_ingredients.append(
                ingredient.model_copy(update={"quantity": scaled_quantity})
            )

        scaled_missing = [
            ingredient.model_copy(update={"quantity": _scaled_quantity(ingredient.quantity, servings)})
            for ingredient in missing
        ]
        nearest_expiry = min(
            (item for item in used_stock if item.expiry_date is not None),
            key=lambda item: item.expiry_date or date.max,
            default=None,
        )
        if nearest_expiry is not None:
            explanation = (
                f"Uses {nearest_expiry.name}, the nearest-dated available ingredient in this recipe "
                f"(use by {nearest_expiry.expiry_date})."
            )
        else:
            explanation = f"Built around available stock, including {used_stock[0].name}."

        return RecipeSuggestion(
            title=recipe.title,
            ingredients=scaled_ingredients,
            steps=recipe.steps,
            preparation_time_minutes=recipe.preparation_time_minutes,
            substitutions=recipe.substitutions,
            servings=servings,
            missing_ingredients=scaled_missing,
            stock_explanation=explanation,
        )