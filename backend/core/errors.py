"""
SynapseOps Error Handling.

Defines custom exception types and FastAPI exception handlers.
Internal errors must not expose stack traces or secrets through API responses.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from backend.core.logging import get_logger

logger = get_logger("core.errors")


# =============================================================================
# Domain Exceptions
# =============================================================================


class SynapseOpsError(Exception):
    """Base exception for all SynapseOps application errors."""


class ConfigurationError(SynapseOpsError):
    """Raised when application configuration is invalid or missing."""


class DatabaseError(SynapseOpsError):
    """Raised when a database operation fails."""


class CacheError(SynapseOpsError):
    """Raised when a cache operation fails."""


class NotFoundError(SynapseOpsError):
    """Raised when a requested resource does not exist."""

    def __init__(self, resource: str, identifier: str) -> None:
        self.resource = resource
        self.identifier = identifier
        super().__init__(f"{resource} with identifier '{identifier}' not found.")


class ValidationError(SynapseOpsError):
    """Raised when domain validation fails beyond Pydantic's built-in checks."""


# =============================================================================
# FastAPI Exception Handlers
# =============================================================================


def register_exception_handlers(app: FastAPI) -> None:
    """Register all application-level exception handlers with the FastAPI app.

    Args:
        app: The FastAPI application instance.
    """

    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
        logger.warning(
            "Resource not found",
            resource=exc.resource,
            identifier=exc.identifier,
            path=str(request.url),
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "not_found", "message": str(exc)},
        )

    @app.exception_handler(SynapseOpsError)
    async def application_error_handler(request: Request, exc: SynapseOpsError) -> JSONResponse:
        logger.error(
            "Application error",
            error_type=type(exc).__name__,
            path=str(request.url),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "internal_error", "message": "An internal error occurred."},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        # Log full details internally, but return a generic message to the client.
        # Never expose internal error details (stack traces, db queries) in responses.
        logger.exception(
            "Unhandled exception",
            error_type=type(exc).__name__,
            path=str(request.url),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "internal_error", "message": "An unexpected error occurred."},
        )
