from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.errors import LeagueNotFound, install_handlers


def test_domain_error_serialized():
    app = FastAPI()
    install_handlers(app)

    @app.get("/boom")
    def boom():
        raise LeagueNotFound("missing")

    r = TestClient(app).get("/boom")
    assert r.status_code == 404
    assert r.json() == {"error_code": "LeagueNotFound", "message": "missing"}
