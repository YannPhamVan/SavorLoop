import json
import sys
from datetime import date, timedelta

from backend.app.gemini_recipes import GeminiRecipeProvider
from backend.app.models import Ingredient
from backend.app.recipe_suggestions import (
    RecipeAPIKeyMissing,
    RecipeInventoryUnavailable,
    RecipeProviderUnavailable,
    RecipeQuotaExhausted,
    RecipeResponseInvalid,
    RecipeSuggestionService,
)


def main() -> int:
    fabricated_inventory = [
        Ingredient(
            category="rotating",
            name="Spinach",
            quantity=1000,
            unit="g",
            expiry_date=date.today() + timedelta(days=5),
        ),
        Ingredient(category="rotating", name="Rice", quantity=2000, unit="g"),
        Ingredient(category="pantry_staple", name="Olive oil", available=True),
    ]

    try:
        suggestion = RecipeSuggestionService(GeminiRecipeProvider()).suggest(
            fabricated_inventory,
            servings=4,
        )
        inventory_names = {item.name.casefold() for item in fabricated_inventory}
        if suggestion.servings != 4:
            raise RecipeResponseInvalid
        if not any(item.name.casefold() in inventory_names for item in suggestion.ingredients):
            raise RecipeResponseInvalid
        if len(suggestion.missing_ingredients) > 2:
            raise RecipeResponseInvalid
        if any(item.quantity <= 0 for item in suggestion.ingredients):
            raise RecipeResponseInvalid
    except RecipeAPIKeyMissing:
        print("SMOKE FAILED: GEMINI_API_KEY is not configured in the backend environment.")
        return 1
    except RecipeQuotaExhausted:
        print("SMOKE FAILED: Gemini free-tier quota is unavailable; check Google AI Studio limits.")
        return 1
    except RecipeProviderUnavailable:
        print("SMOKE FAILED: Gemini is unavailable or GEMINI_MODEL is not accepted.")
        return 1
    except (RecipeInventoryUnavailable, RecipeResponseInvalid):
        print("SMOKE FAILED: the generated recipe did not pass validation for the fabricated inventory.")
        return 1
    except Exception:
        print("SMOKE FAILED: recipe generation could not be verified.")
        return 1

    print("SMOKE PASSED: live Gemini recipe generated from fabricated inventory for 4 servings.")
    print(json.dumps(suggestion.model_dump(mode="json"), indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())