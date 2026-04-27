from fastapi import FastAPI

from app.api import api_router
from app.errors import install_handlers


def create_app() -> FastAPI:
    app = FastAPI(title="Hockey Manager")
    install_handlers(app)
    app.include_router(api_router)
    return app


app = create_app()
