"""Database engine, ORM base, and session configuration."""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DATABASE_URL = "postgresql+psycopg://localhost/flower_ai"

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


def get_db() -> Iterator[Session]:
    """Provide a database session and close it after the request finishes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class Base(DeclarativeBase):
    """Base class for SQLAlchemy ORM models."""
