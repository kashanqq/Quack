"""FastAPI application factory without infrastructure connections."""

from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from app.api.health import router as health_router
from app.errors import AppError


def create_app() -> FastAPI:
    app = FastAPI(title="Quack API")

    @app.middleware("http")
    async def request_id_middleware(
        request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request.state.request_id = (
            request.headers.get("X-Request-Id") or uuid4().hex[:16]
        )
        response = await call_next(request)
        response.headers["X-Request-Id"] = request.state.request_id
        return response

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "validation_failed",
                    "message": "Request validation failed",
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        # ServerErrorMiddleware handles these outside the request-id middleware.
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "internal", "message": "Internal server error"}},
            headers={"X-Request-Id": request.state.request_id},
        )

    app.include_router(health_router)
    return app
