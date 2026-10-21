import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase

DEFAULT_DATABASE_URL = "sqlite:///./savorloop.db"


class Base(DeclarativeBase):
    pass


def create_database_engine(database_url: str | None = None) -> Engine:
    configured_url = database_url or os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
    connect_args = {"check_same_thread": False} if configured_url.startswith("sqlite:") else {}
    return create_engine(configured_url, connect_args=connect_args, pool_pre_ping=True)


engine = create_database_engine()