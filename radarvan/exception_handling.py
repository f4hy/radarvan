"""Global FastAPI exception handler — notifies on unhandled exceptions and returns a
generic 500 JSON response (``setup_error_handling``)."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from . import notify


def setup_error_handling(app: FastAPI) -> None:
    @app.exception_handler(Exception)
    async def global_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        notify.notify(f"Unhandled Exception {request.url.path} {exc!r}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": str(exc),
                "path": request.url.path,
            },
        )
