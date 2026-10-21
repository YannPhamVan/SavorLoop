import json
import os

from google import genai

from backend.app.recipe_suggestions import (
    RecipeAPIKeyMissing,
    RecipeModelOutput,
    RecipeProviderUnavailable,
    RecipeQuotaExhausted,
    RecipeStockItem,
)

DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"


class GeminiRecipeProvider:
    def __init__(self, model: str | None = None) -> None:
        configured_model = model if model is not None else os.environ.get("GEMINI_MODEL", "")
        self.model = configured_model.strip() or DEFAULT_GEMINI_MODEL
        self._client = None

    def generate(
        self,
        stock: list[RecipeStockItem],
        requested_servings: int,
        correction: str | None = None,
    ) -> object:
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise RecipeAPIKeyMissing from None

        stock_payload = [item.model_dump(mode="json") for item in stock]
        prompt = (
            "Create one practical recipe using the supplied available kitchen stock. "
            "Return quantities for exactly two base servings; the backend will scale quantities "
            f"to {requested_servings} requested servings. Keep scaled amounts within each listed "
            "rotating stock quantity, and use its listed unit without conversion. Prefer suitable "
            "ingredients with earlier use-by dates. Use exact stock names when an item is available. "
            "Use no more than two ingredients absent from stock. Include ordered, concise cooking "
            "steps, preparation time in minutes, and practical substitutions. Do not include "
            "serving counts or missing-ingredient fields.\n"
            f"Available stock: {json.dumps(stock_payload, ensure_ascii=True)}"
        )
        if correction:
            prompt += f"\nCorrection: {correction}"

        try:
            if self._client is None:
                self._client = genai.Client(api_key=api_key)
            response = self._client.interactions.create(
                model=self.model,
                input=prompt,
                response_format={
                    "type": "text",
                    "mime_type": "application/json",
                    "schema": RecipeModelOutput.model_json_schema(),
                },
                generation_config={"thinking_level": "low", "max_output_tokens": 1200},
                store=False,
            )
            return response.output_text
        except Exception as exc:
            if getattr(exc, "status_code", None) == 429 or getattr(exc, "code", None) == 429:
                raise RecipeQuotaExhausted from None
            raise RecipeProviderUnavailable from None