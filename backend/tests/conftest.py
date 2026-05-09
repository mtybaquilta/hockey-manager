import os

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401  (register tables on Base.metadata)
from app.db import Base
from app.services.league_service import create_or_reset_league

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


@pytest.fixture()
def db_with_league(db):
    create_or_reset_league(db, seed=12345)
    return db


@pytest.fixture()
def db_factory(engine):
    """Return a factory that creates a fresh league with the given seed.

    Each call drops and recreates all tables so both runs start clean,
    making determinism tests possible within one pytest session.
    The session is committed so all locks are released before the caller
    reads or the next call to make() drops the tables.
    """
    sessions: list = []

    def make(seed: int):
        # Close any sessions from previous calls so drop_all can proceed.
        for prev in sessions:
            try:
                prev.close()
            except Exception:
                pass
        sessions.clear()

        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        S = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
        s = S()
        create_or_reset_league(s, seed=seed)
        s.commit()  # Release locks so drop_all on next call can proceed.
        sessions.append(s)
        return s

    yield make

    # Teardown: db_factory tests can leave Postgres backends in
    # 'idle in transaction' (e.g. SQLAlchemy autobegin reopened a closed
    # session). Forcibly terminate any non-self backend on this database so
    # the next test starts clean and TRUNCATE doesn't deadlock.
    for prev in sessions:
        try:
            prev.close()
        except Exception:
            pass
    sessions.clear()
    engine.dispose()
    from sqlalchemy import text

    with engine.connect() as conn:
        conn.execute(
            text(
                "SELECT pg_terminate_backend(pid) "
                "FROM pg_stat_activity "
                "WHERE datname = current_database() AND pid <> pg_backend_pid()"
            )
        )
        conn.commit()
    table_names = ", ".join(
        f'"{t.name}"' for t in reversed(Base.metadata.sorted_tables)
    )
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {table_names} RESTART IDENTITY CASCADE"))
