from fastapi.testclient import TestClient

from app.db import get_db
from app.main import app
from app.services.league_service import create_or_reset_league


def _client(db):
    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    return TestClient(app)


def _setup(db, seed=42):
    create_or_reset_league(db, seed=seed)
    db.flush()


def test_list_skaters_returns_pool(db):
    _setup(db)
    try:
        client = _client(db)
        r = client.get("/api/free-agents/skaters")
        assert r.status_code == 200
        rows = r.json()
        assert len(rows) == 40
        # All have ovr computed
        assert all("ovr" in r for r in rows)
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_list_skaters_filter_by_position(db):
    _setup(db)
    try:
        client = _client(db)
        r = client.get("/api/free-agents/skaters?position=C")
        rows = r.json()
        assert len(rows) == 8
        assert all(p["position"] == "C" for p in rows)
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_list_skaters_min_ovr(db):
    _setup(db)
    try:
        client = _client(db)
        r = client.get("/api/free-agents/skaters?min_ovr=70")
        rows = r.json()
        assert all(p["ovr"] >= 70 for p in rows)
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_list_skaters_sort_age_asc(db):
    _setup(db)
    try:
        client = _client(db)
        r = client.get("/api/free-agents/skaters?sort=age&order=asc")
        ages = [p["age"] for p in r.json()]
        assert ages == sorted(ages)
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_list_skaters_max_age(db):
    _setup(db)
    try:
        client = _client(db)
        r = client.get("/api/free-agents/skaters?max_age=25")
        rows = r.json()
        assert all(p["age"] <= 25 for p in rows)
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_list_goalies(db):
    _setup(db)
    try:
        client = _client(db)
        r = client.get("/api/free-agents/goalies")
        assert r.status_code == 200
        rows = r.json()
        assert len(rows) == 5
        assert all("ovr" in g for g in rows)
    finally:
        app.dependency_overrides.pop(get_db, None)
