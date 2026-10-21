from collections.abc import Iterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.database import engine
from backend.app.gemini_recipes import GeminiRecipeProvider
from backend.app.inventory_updates import (
    InventoryInterpreter,
    InventoryOperationRejected,
    InventoryUpdateRequest,
    InventoryUpdateResult,
    configured_inventory_interpreter,
    parse_inventory_plan,
    validate_inventory_plan,
)
from backend.app.models import Base, Ingredient
from backend.app.recipe_suggestions import (
    RecipeAPIKeyMissing,
    RecipeInventoryUnavailable,
    RecipeProviderUnavailable,
    RecipeQuotaExhausted,
    RecipeResponseInvalid,
    RecipeSuggestion,
    RecipeSuggestionRequest,
    RecipeSuggestionService,
)
from backend.app.schemas import IngredientRead, IngredientWrite


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="SavorLoop API", lifespan=lifespan)
app.state.inventory_interpreter = configured_inventory_interpreter()
app.state.recipe_suggester = RecipeSuggestionService(GeminiRecipeProvider())


@app.exception_handler(RequestValidationError)
async def validation_error_response(_: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [
        {"type": error["type"], "loc": error["loc"], "msg": error["msg"]}
        for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": errors})


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session


def get_inventory_interpreter(request: Request) -> InventoryInterpreter:
    return request.app.state.inventory_interpreter


def get_recipe_suggester(request: Request) -> RecipeSuggestionService:
    return request.app.state.recipe_suggester


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict[str, str]:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
    return {"status": "ready"}


@app.get("/api/inventory", response_model=list[IngredientRead])
def list_inventory(session: Session = Depends(get_session)) -> list[Ingredient]:
    statement = select(Ingredient).order_by(Ingredient.category, Ingredient.name, Ingredient.id)
    return list(session.scalars(statement))


@app.post("/api/suggestions", response_model=RecipeSuggestion)
def create_recipe_suggestion(
    suggestion_request: RecipeSuggestionRequest,
    session: Session = Depends(get_session),
    suggester: RecipeSuggestionService = Depends(get_recipe_suggester),
) -> RecipeSuggestion:
    inventory = list(session.scalars(select(Ingredient)))
    try:
        return suggester.suggest(inventory, suggestion_request.servings)
    except RecipeAPIKeyMissing as exc:
        raise HTTPException(
            status_code=503,
            detail="Recipe suggestions are not configured. Set GEMINI_API_KEY in the backend .env and restart the API.",
        ) from exc
    except RecipeQuotaExhausted as exc:
        raise HTTPException(
            status_code=429,
            detail="Gemini's free-tier quota is unavailable. Wait for its quota to reset or check your Google AI Studio limits.",
        ) from exc
    except RecipeProviderUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail="Recipe suggestions are temporarily unavailable. Check GEMINI_MODEL and provider status, then try again.",
        ) from exc
    except RecipeInventoryUnavailable as exc:
        raise HTTPException(
            status_code=422,
            detail="Add at least one available ingredient before requesting a recipe.",
        ) from exc
    except RecipeResponseInvalid as exc:
        raise HTTPException(
            status_code=502,
            detail="The recipe response could not be validated after one correction attempt. No suggestion was saved; try again later.",
        ) from exc


@app.post("/api/inventory/natural-language", response_model=InventoryUpdateResult)
def update_inventory_from_natural_language(
    update_request: InventoryUpdateRequest,
    session: Session = Depends(get_session),
    interpreter: InventoryInterpreter = Depends(get_inventory_interpreter),
) -> InventoryUpdateResult:
    correction: str | None = None
    validated_changes = None

    for attempt in range(2):
        try:
            model_output = interpreter.interpret(update_request.text, correction)
        except Exception as exc:
            detail = (
                "Natural-language updates are not configured or are temporarily unavailable. "
                "Use the inventory controls instead."
            )
            raise HTTPException(status_code=503, detail=detail) from exc

        try:
            plan = parse_inventory_plan(model_output)
            validated_changes = validate_inventory_plan(session, plan)
            break
        except InventoryOperationRejected as exc:
            session.rollback()
            if attempt == 1:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            correction = str(exc)

    if validated_changes is None:
        raise HTTPException(status_code=422, detail="The inventory update could not be validated.")

    for ingredient, operation in validated_changes:
        if operation.action == "set_available":
            ingredient.available = True
        elif operation.action == "set_unavailable":
            ingredient.available = False
        else:
            ingredient.quantity = (ingredient.quantity or 0) - (operation.amount or 0)

    try:
        session.commit()
    except SQLAlchemyError as exc:
        session.rollback()
        raise HTTPException(
            status_code=503,
            detail="Inventory could not be updated. No changes were saved; try again.",
        ) from exc

    return InventoryUpdateResult(
        status="updated",
        message="Inventory updated.",
        updated_count=len(validated_changes),
    )


@app.post(
    "/api/inventory",
    response_model=IngredientRead,
    status_code=status.HTTP_201_CREATED,
)
def create_ingredient(
    ingredient_data: IngredientWrite,
    session: Session = Depends(get_session),
) -> Ingredient:
    ingredient = Ingredient(**ingredient_data.model_dump())
    session.add(ingredient)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=422, detail="Invalid ingredient data") from exc
    session.refresh(ingredient)
    return ingredient


@app.put("/api/inventory/{ingredient_id}", response_model=IngredientRead)
def update_ingredient(
    ingredient_id: int,
    ingredient_data: IngredientWrite,
    session: Session = Depends(get_session),
) -> Ingredient:
    ingredient = session.get(Ingredient, ingredient_id)
    if ingredient is None:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    for field, value in ingredient_data.model_dump().items():
        setattr(ingredient, field, value)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=422, detail="Invalid ingredient data") from exc
    session.refresh(ingredient)
    return ingredient


@app.delete("/api/inventory/{ingredient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ingredient(ingredient_id: int, session: Session = Depends(get_session)) -> Response:
    ingredient = session.get(Ingredient, ingredient_id)
    if ingredient is None:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    session.delete(ingredient)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)