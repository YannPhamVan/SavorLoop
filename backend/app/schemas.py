from datetime import date
from math import isfinite
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

IngredientCategory = Literal["pantry_staple", "rotating"]


class IngredientWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: IngredientCategory
    name: str
    available: bool | None = None
    quantity: float | None = None
    unit: str | None = None
    expiry_date: date | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Name cannot be empty")
        return normalized

    @field_validator("unit")
    @classmethod
    def normalize_unit(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def validate_category_fields(self) -> "IngredientWrite":
        if self.category == "pantry_staple":
            if self.available is None:
                raise ValueError("Pantry staples require an available status")
            if self.model_fields_set.intersection({"quantity", "unit", "expiry_date"}):
                raise ValueError("Pantry staples cannot include quantity, unit, or expiry date")
        else:
            if "available" in self.model_fields_set:
                raise ValueError("Rotating ingredients do not have an available status")
            if self.quantity is None or not isfinite(self.quantity) or self.quantity <= 0:
                raise ValueError("Quantity must be a positive finite number")
            if not self.unit:
                raise ValueError("Rotating ingredients require a unit")
        return self


class IngredientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category: IngredientCategory
    name: str
    available: bool | None
    quantity: float | None
    unit: str | None
    expiry_date: date | None