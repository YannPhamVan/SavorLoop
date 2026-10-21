from datetime import date

from sqlalchemy import Boolean, CheckConstraint, Date, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


class Ingredient(Base):
    __tablename__ = "ingredients"
    __table_args__ = (
        CheckConstraint(
            "category IN ('pantry_staple', 'rotating')",
            name="ck_ingredients_category",
        ),
        CheckConstraint(
            "(category = 'pantry_staple' AND available IS NOT NULL "
            "AND quantity IS NULL AND unit IS NULL AND expiry_date IS NULL) OR "
            "(category = 'rotating' AND available IS NULL AND quantity > 0 "
            "AND quantity < 1.7976931348623157e308 AND unit IS NOT NULL "
            "AND length(trim(unit)) > 0)",
            name="ck_ingredients_category_fields",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    available: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(40), nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)


class NotebookRecipe(Base):
    __tablename__ = "notebook_recipes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    attempts: Mapped[list["CookingAttempt"]] = relationship(
        back_populates="recipe",
        cascade="all, delete-orphan",
        order_by="CookingAttempt.id",
    )


class CookingAttempt(Base):
    __tablename__ = "cooking_attempts"
    __table_args__ = (CheckConstraint("rating BETWEEN 1 AND 5", name="ck_cooking_attempts_rating"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("notebook_recipes.id"), nullable=False)
    attempt_date: Mapped[date] = mapped_column(Date, nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comments: Mapped[str] = mapped_column(String(2000), nullable=False, default="")
    changes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    substitutions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    liked_adjustments: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    recipe: Mapped[NotebookRecipe] = relationship(back_populates="attempts")