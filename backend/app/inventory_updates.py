import os
import re
import unicodedata
from math import isfinite
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import Ingredient


class InventoryOperation(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    action: Literal["set_available", "set_unavailable", "consume"]
    ingredient: str = Field(min_length=1, max_length=120)
    amount: float | None = None
    unit: str | None = Field(default=None, max_length=40)

    @field_validator("unit")
    @classmethod
    def normalize_unit(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def validate_action_fields(self) -> "InventoryOperation":
        if self.action == "consume":
            if self.amount is None or not isfinite(self.amount) or self.amount <= 0:
                raise ValueError("Consumption requires a positive finite quantity")
            if not self.unit:
                raise ValueError("Consumption requires a unit")
        elif self.amount is not None or self.unit is not None:
            raise ValueError("Availability changes cannot include a quantity or unit")
        return self


class InventoryUpdatePlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operations: list[InventoryOperation] = Field(min_length=1, max_length=20)


class InventoryUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    text: str = Field(min_length=1, max_length=1000)


class InventoryUpdateResult(BaseModel):
    status: Literal["updated"]
    message: str
    updated_count: int


class InventoryInterpreter(Protocol):
    def interpret(self, text: str, correction: str | None = None) -> object: ...


class InventoryProviderUnavailable(RuntimeError):
    pass


class UnconfiguredInventoryInterpreter:
    def interpret(self, text: str, correction: str | None = None) -> object:
        raise InventoryProviderUnavailable


class DemoInventoryInterpreter:
    _availability = re.compile(
        r"^(?:mark|set)\s+(?P<ingredient>.+?)\s+(?P<state>available|unavailable)[.!]?\s*$",
        re.IGNORECASE,
    )
    _consumption = re.compile(
        r"^(?:consume|use)\s+(?P<amount>\d+(?:\.\d+)?)\s+(?P<unit>[a-zA-Z]+)\s+(?:of\s+)?(?P<ingredient>.+?)[.!]?\s*$",
        re.IGNORECASE,
    )

    def interpret(self, text: str, correction: str | None = None) -> object:
        availability = self._availability.fullmatch(text.strip())
        if availability:
            action = "set_available" if availability["state"].casefold() == "available" else "set_unavailable"
            return {"operations": [{"action": action, "ingredient": availability["ingredient"]}]}

        consumption = self._consumption.fullmatch(text.strip())
        if consumption:
            return {
                "operations": [
                    {
                        "action": "consume",
                        "ingredient": consumption["ingredient"],
                        "amount": float(consumption["amount"]),
                        "unit": consumption["unit"],
                    }
                ]
            }
        return {"operations": []}


def configured_inventory_interpreter() -> InventoryInterpreter:
    if os.environ.get("SAVORLOOP_INVENTORY_INTERPRETER", "").strip().casefold() == "demo":
        return DemoInventoryInterpreter()
    return UnconfiguredInventoryInterpreter()


class InventoryOperationRejected(ValueError):
    pass


def _normalize(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).split()).casefold()


def validate_inventory_plan(
    session: Session,
    plan: InventoryUpdatePlan,
) -> list[tuple[Ingredient, InventoryOperation]]:
    inventory = list(session.scalars(select(Ingredient)))
    validated: list[tuple[Ingredient, InventoryOperation]] = []
    seen_ingredient_ids: set[int] = set()

    for operation in plan.operations:
        normalized_name = _normalize(operation.ingredient)
        matches = [item for item in inventory if _normalize(item.name) == normalized_name]
        if not matches:
            raise InventoryOperationRejected(
                "No inventory item matches that name. Check the name and try again."
            )
        if len(matches) > 1:
            raise InventoryOperationRejected(
                "More than one inventory item matches. Use an exact, unambiguous name."
            )

        ingredient = matches[0]
        if ingredient.id in seen_ingredient_ids:
            raise InventoryOperationRejected(
                "Use one change per inventory item in a request."
            )
        seen_ingredient_ids.add(ingredient.id)

        if operation.action in {"set_available", "set_unavailable"}:
            if ingredient.category != "pantry_staple":
                raise InventoryOperationRejected(
                    "Availability changes apply only to pantry staples."
                )
        else:
            if ingredient.category != "rotating":
                raise InventoryOperationRejected(
                    "Consumption requires a rotating ingredient with a recorded quantity."
                )
            if _normalize(operation.unit or "") != _normalize(ingredient.unit or ""):
                raise InventoryOperationRejected(
                    "The requested unit does not match the recorded unit. Use the listed unit; automatic conversion is not supported."
                )
            remaining = (ingredient.quantity or 0) - (operation.amount or 0)
            if not isfinite(remaining) or remaining <= 0:
                raise InventoryOperationRejected(
                    "That amount exceeds the usable recorded stock. Reduce it or update the stock using the inventory controls."
                )

        validated.append((ingredient, operation))

    return validated


def parse_inventory_plan(value: object) -> InventoryUpdatePlan:
    try:
        return InventoryUpdatePlan.model_validate(value)
    except ValidationError as exc:
        raise InventoryOperationRejected(
            "I couldn't safely interpret that request. Restate it with an item name and a supported change."
        ) from exc