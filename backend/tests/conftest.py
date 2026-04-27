import os

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401  (register tables on Base.metadata)
from app.db import Base

TEST_DB_URL = os.environ.get(
    "HM_TEST_DATABASE_URL",
    "postgresql+psycopg://jonas@localhost:5432/hockey_manager",
)


@pytest.fixture(scope="session")
def engine():
    eng = create_engine(TEST_DB_URL, future=True)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture()
def db(engine):
    """Single-DB fixture: each test runs inside an outer transaction that
    always rolls back. Service-level commits map to SAVEPOINT releases, so
    they don't escape the test boundary."""
    connection = engine.connect()
    outer = connection.begin()
    Session = sessionmaker(bind=connection, autoflush=False, autocommit=False, future=True, join_transaction_mode="create_savepoint")
    session = Session()
    try:
        yield session
    finally:
        session.close()
        outer.rollback()
        connection.close()
