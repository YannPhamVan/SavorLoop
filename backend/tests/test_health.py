import asyncio

import httpx
from sqlalchemy.exc import OperationalError

from backend.app import main
from backend.app.database import create_database_engine


class UnavailableEngine:
    def connect(self):
        raise OperationalError("SELECT 1", {}, RuntimeError("database unavailable"))


def get_response(path: str) -> httpx.Response:
    async def send_request() -> httpx.Response:
        transport = httpx.ASGITransport(app=main.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get(path)

    return asyncio.run(send_request())


def test_smoke_health_returns_200() -> None:
    response = get_response("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_does_not_depend_on_database(monkeypatch) -> None:
    monkeypatch.setattr(main, "engine", UnavailableEngine())

    response = get_response("/health")

    assert response.status_code == 200


def test_ready_returns_200_for_reachable_database(monkeypatch, tmp_path) -> None:
    engine = create_database_engine(f"sqlite:///{tmp_path / 'ready.db'}")
    monkeypatch.setattr(main, "engine", engine)

    try:
        response = get_response("/ready")
    finally:
        engine.dispose()

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_ready_returns_503_for_unreachable_database(monkeypatch) -> None:
    monkeypatch.setattr(main, "engine", UnavailableEngine())

    response = get_response("/ready")

    assert response.status_code == 503


def test_database_url_configures_sqlite_connection(monkeypatch, tmp_path) -> None:
    database_path = tmp_path / "configured.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")
    engine = create_database_engine()

    try:
        with engine.connect() as connection:
            assert connection.exec_driver_sql("SELECT 1").scalar_one() == 1
        assert engine.url.database == str(database_path)
    finally:
        engine.dispose()