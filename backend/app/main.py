import os
import sqlite3
from collections.abc import Iterator
from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from opentelemetry import propagate
from opentelemetry.trace import SpanKind, Status, StatusCode
from sqlalchemy import Engine, event, select, text
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

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
from backend.app.models import Base, CookingAttempt, Ingredient, NotebookRecipe
from backend.app.notebook import (
    CookingAttemptRead,
    CookingAttemptWrite,
    NotebookRecipeCreate,
    NotebookRecipeRead,
    make_attempt,
    recipe_to_read,
    select_recipe_feedback,
)
from backend.app.on_call import OnCallAgent, ReadinessAlert, read_database_readiness
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
from backend.app.telemetry import Telemetry, configured_telemetry


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="SavorLoop API", lifespan=lifespan)
app.state.inventory_interpreter = configured_inventory_interpreter()
app.state.recipe_suggester = RecipeSuggestionService(GeminiRecipeProvider())
app.state.telemetry = configured_telemetry()


def require_on_call_test_mode() -> None:
    if (
        os.environ.get("SAVORLOOP_ON_CALL_TEST_MODE") != "1"
        or engine.dialect.name != "sqlite"
    ):
        raise HTTPException(status_code=404, detail="Not found")


def arm_stale_connection_readiness_failure(engine: Engine) -> None:
    with engine.connect() as connection:
        stale_connection = connection.connection.driver_connection

    @event.listens_for(engine, "before_cursor_execute")
    def fail_stale_readiness_probe(
        db_connection,
        _cursor,
        statement,
        parameters,
        _context,
        _executemany,
    ) -> None:
        if (
            db_connection.connection.driver_connection is stale_connection
            and statement.strip().upper() == "SELECT 1"
        ):
            raise OperationalError(
                statement,
                parameters,
                sqlite3.OperationalError("synthetic stale pooled connection"),
            )


def mount_frontend(application: FastAPI, frontend_directory: Path) -> None:
    if frontend_directory.is_dir():
        application.mount(
            "/",
            StaticFiles(directory=frontend_directory, html=True),
            name="frontend",
        )


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


def get_telemetry(request: Request) -> Telemetry:
    return request.app.state.telemetry


@app.middleware("http")
async def instrument_inventory_update(request: Request, call_next):
    if request.method != "POST" or request.url.path != "/api/inventory/natural-language":
        return await call_next(request)

    telemetry: Telemetry = request.app.state.telemetry
    started_at = perf_counter()
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    parent_context = propagate.extract(request.headers)
    span_attributes = {
        "operation.name": "inventory_update",
        "http.request.method": "POST",
        "http.route": "/api/inventory/natural-language",
    }

    with telemetry.tracer.start_as_current_span(
        "inventory.request",
        context=parent_context,
        kind=SpanKind.SERVER,
        attributes=span_attributes,
        record_exception=False,
        set_status_on_exception=False,
    ) as request_span:
        try:
            response = await call_next(request)
            status_code = response.status_code
            with telemetry.tracer.start_as_current_span(
                "inventory.response",
                attributes={"http.response.status_code": status_code},
            ):
                pass
            return response
        except Exception:
            request.state.telemetry_error_category = "internal"
            request_span.set_status(Status(StatusCode.ERROR))
            raise
        finally:
            duration_seconds = perf_counter() - started_at
            error_category = getattr(request.state, "telemetry_error_category", None)
            if status_code >= 400 and error_category is None:
                error_category = (
                    "request_validation"
                    if status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
                    else "request_failed"
                )
            telemetry.record_inventory_update(
                status="error" if status_code >= 400 else "success",
                duration_seconds=duration_seconds,
                error_category=error_category,
            )
            request_span.set_attribute("http.response.status_code", status_code)
            if status_code >= 400:
                request_span.set_attribute("error.category", error_category or "request_failed")
                request_span.set_status(Status(StatusCode.ERROR))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict[str, str]:
    if not read_database_readiness(engine).ready:
        raise HTTPException(status_code=503, detail="Database unavailable")
    return {"status": "ready"}


@app.post("/internal/ops/test/arm-stale-readiness-failure", include_in_schema=False)
def arm_test_readiness_failure(request: Request) -> dict[str, str]:
    require_on_call_test_mode()
    if getattr(request.app.state, "on_call_fault_armed", False):
        raise HTTPException(status_code=409, detail="Test failure already armed")
    arm_stale_connection_readiness_failure(engine)
    request.app.state.on_call_fault_armed = True
    return {"status": "armed"}


@app.post("/internal/ops/test/alert", include_in_schema=False)
def dispatch_test_alert(alert: ReadinessAlert, request: Request) -> dict:
    require_on_call_test_mode()
    return OnCallAgent(engine).handle_alert(alert)


@app.get("/api/inventory", response_model=list[IngredientRead])
def list_inventory(session: Session = Depends(get_session)) -> list[Ingredient]:
    statement = select(Ingredient).order_by(Ingredient.category, Ingredient.name, Ingredient.id)
    return list(session.scalars(statement))


@app.get("/api/notebook", response_model=list[NotebookRecipeRead])
def list_notebook(session: Session = Depends(get_session)) -> list[NotebookRecipeRead]:
    recipes = session.scalars(
        select(NotebookRecipe)
        .options(selectinload(NotebookRecipe.attempts))
        .order_by(NotebookRecipe.id)
    )
    return [recipe_to_read(recipe) for recipe in recipes]


@app.post(
    "/api/notebook",
    response_model=NotebookRecipeRead,
    status_code=status.HTTP_201_CREATED,
)
def confirm_recipe_cooked(
    payload: NotebookRecipeCreate,
    session: Session = Depends(get_session),
) -> NotebookRecipeRead:
    recipe = NotebookRecipe(snapshot=payload.recipe.model_dump(mode="json"))
    recipe.attempts.append(make_attempt(payload.attempt))
    session.add(recipe)
    try:
        session.commit()
    except SQLAlchemyError as exc:
        session.rollback()
        raise HTTPException(
            status_code=503,
            detail="The cooking note could not be saved. No changes were saved; try again.",
        ) from exc
    session.refresh(recipe)
    return recipe_to_read(recipe)


@app.post(
    "/api/notebook/{recipe_id}/attempts",
    response_model=CookingAttemptRead,
    status_code=status.HTTP_201_CREATED,
)
def add_cooking_attempt(
    recipe_id: int,
    payload: CookingAttemptWrite,
    session: Session = Depends(get_session),
) -> CookingAttempt:
    recipe = session.get(NotebookRecipe, recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Notebook recipe not found")
    attempt = make_attempt(payload)
    recipe.attempts.append(attempt)
    try:
        session.commit()
    except SQLAlchemyError as exc:
        session.rollback()
        raise HTTPException(
            status_code=503,
            detail="The cooking attempt could not be saved. No changes were saved; try again.",
        ) from exc
    session.refresh(attempt)
    return attempt


@app.post("/api/suggestions", response_model=RecipeSuggestion)
def create_recipe_suggestion(
    suggestion_request: RecipeSuggestionRequest,
    session: Session = Depends(get_session),
    suggester: RecipeSuggestionService = Depends(get_recipe_suggester),
) -> RecipeSuggestion:
    inventory = list(session.scalars(select(Ingredient)))
    feedback_context = select_recipe_feedback(session)
    try:
        return suggester.suggest(inventory, suggestion_request.servings, feedback_context)
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
    request: Request,
    session: Session = Depends(get_session),
    interpreter: InventoryInterpreter = Depends(get_inventory_interpreter),
    telemetry: Telemetry = Depends(get_telemetry),
) -> InventoryUpdateResult:
    correction: str | None = None
    validated_changes = None

    for attempt in range(2):
        with telemetry.tracer.start_as_current_span(
            "inventory.update.provider",
            attributes={"ai.attempt": attempt + 1},
            record_exception=False,
            set_status_on_exception=False,
        ) as provider_span:
            try:
                model_output = interpreter.interpret(update_request.text, correction)
            except Exception as exc:
                provider_span.set_attribute("error.category", "provider_unavailable")
                provider_span.set_status(Status(StatusCode.ERROR))
                request.state.telemetry_error_category = "provider_unavailable"
                detail = (
                    "Natural-language updates are not configured or are temporarily unavailable. "
                    "Use the inventory controls instead."
                )
                raise HTTPException(status_code=503, detail=detail) from exc

        with telemetry.tracer.start_as_current_span(
            "inventory.update.validation",
            attributes={"ai.attempt": attempt + 1},
            record_exception=False,
            set_status_on_exception=False,
        ) as validation_span:
            try:
                plan = parse_inventory_plan(model_output)
                validated_changes = validate_inventory_plan(session, plan)
                validation_span.set_attribute("validation.result", "accepted")
                break
            except InventoryOperationRejected as exc:
                validation_span.set_attribute("validation.result", "rejected")
                validation_span.set_attribute("error.category", "ai_validation")
                validation_span.set_status(Status(StatusCode.ERROR))
                session.rollback()
                if attempt == 1:
                    request.state.telemetry_error_category = "ai_validation"
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

    with telemetry.tracer.start_as_current_span(
        "inventory.update.database.write",
        record_exception=False,
        set_status_on_exception=False,
    ) as database_span:
        try:
            session.commit()
        except SQLAlchemyError as exc:
            database_span.set_attribute("error.category", "database")
            database_span.set_status(Status(StatusCode.ERROR))
            session.rollback()
            request.state.telemetry_error_category = "database"
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


mount_frontend(app, Path(__file__).resolve().parents[2] / "frontend" / "dist")