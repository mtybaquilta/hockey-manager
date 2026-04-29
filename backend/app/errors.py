from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class DomainError(Exception):
    code: str = "DomainError"
    status: int = 400

    def __init__(self, message: str = ""):
        super().__init__(message or self.code)
        self.message = message or self.code


class LeagueNotFound(DomainError):
    code = "LeagueNotFound"
    status = 404


class TeamNotFound(DomainError):
    code = "TeamNotFound"
    status = 404


class GameNotFound(DomainError):
    code = "GameNotFound"
    status = 404


class SkaterNotFound(DomainError):
    code = "SkaterNotFound"
    status = 404


class GoalieNotFound(DomainError):
    code = "GoalieNotFound"
    status = 404


class LineupInvalid(DomainError):
    code = "LineupInvalid"
    status = 422


class LineupSlotConflict(DomainError):
    code = "LineupSlotConflict"
    status = 422


class SeasonAlreadyComplete(DomainError):
    code = "SeasonAlreadyComplete"
    status = 409


def install_handlers(app: FastAPI) -> None:
    async def handle(_request: Request, exc: DomainError):
        return JSONResponse(
            status_code=exc.status,
            content={"error_code": exc.code, "message": exc.message},
        )

    app.add_exception_handler(DomainError, handle)
