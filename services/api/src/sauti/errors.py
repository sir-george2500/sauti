"""RFC7807-ish error envelope: {code, message, detail?}."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse


class ApiError(HTTPException):
    def __init__(self, status_code: int, code: str, message: str, detail: object | None = None):
        super().__init__(status_code=status_code, detail=message)
        self.code = code
        self.message = message
        self.extra_detail = detail


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
        body: dict = {"code": exc.code, "message": exc.message}
        if exc.extra_detail is not None:
            body["detail"] = exc.extra_detail
        return JSONResponse(status_code=exc.status_code, content=body, headers=exc.headers)

    @app.exception_handler(HTTPException)
    async def http_error_handler(_: Request, exc: HTTPException) -> JSONResponse:
        code = {401: "UNAUTHORIZED", 403: "FORBIDDEN", 404: "NOT_FOUND", 429: "RATE_LIMITED"}.get(
            exc.status_code, "ERROR"
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": code, "message": str(exc.detail)},
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Strip echoed input values (pydantic v2 puts the submitted value in
        # "input"/"ctx") — a failed LoginIn would otherwise reflect the password.
        detail = [
            {k: v for k, v in err.items() if k in ("type", "loc", "msg")}
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={"code": "VALIDATION", "message": "Invalid request", "detail": detail},
        )
