from collections.abc import Iterator
from os import getenv

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import DATABASE_URL, Base

TEST_DATABASE_URL = getenv("TEST_DATABASE_URL")


@pytest.fixture
def db_session() -> Iterator[Session]:
    if TEST_DATABASE_URL:
        test_url = make_url(TEST_DATABASE_URL)
        application_url = make_url(DATABASE_URL)

        if test_url.set(drivername=application_url.drivername) == application_url:
            raise RuntimeError("TEST_DATABASE_URL must not point to the app database")

        engine = create_engine(TEST_DATABASE_URL)
    else:
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        @event.listens_for(engine, "connect")
        def enable_foreign_keys(connection, _connection_record):
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as session:
        yield session

    Base.metadata.drop_all(engine)
    engine.dispose()