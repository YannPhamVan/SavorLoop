from collections.abc import Iterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.database import engine
from backend.app.models import Base, Ingredient
from backend.app.schemas import IngredientRead, IngredientWrite


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="SavorLoop API", lifespan=lifespan)


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