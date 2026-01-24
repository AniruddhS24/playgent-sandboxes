import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class SyntheticDataError(Exception):
    """Base exception for synthetic data operations."""
    pass


class RecordNotFoundError(SyntheticDataError):
    """Raised when the specified record doesn't exist."""
    pass


class KeyPathError(SyntheticDataError):
    """Raised when the key path is invalid or doesn't exist."""
    pass


class SchemaValidationError(SyntheticDataError):
    """Raised when data doesn't match the required schema."""
    pass


class ActionNotFoundError(SyntheticDataError):
    """Raised when the specified action doesn't exist."""
    pass


class ActionExecutionError(SyntheticDataError):
    """Raised when action execution fails."""
    pass


class GenerationError(SyntheticDataError):
    """Raised when synthetic data generation fails."""
    pass


class ScenarioCollectionError(GenerationError):
    """Raised when there's an issue collecting scenarios."""
    pass


class PlanGenerationError(GenerationError):
    """Raised when generation plan creation fails."""
    pass


def init_error_handlers(app: FastAPI):
    @app.exception_handler(Exception)
    async def exception_handler(request: Request, e: Exception):
        logger.error(f"Error during request: {e}", exc_info=e)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=jsonable_encoder({"error": str(e)}),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, e: HTTPException):
        logger.error(f"Error during request: {e}", exc_info=e)
        return JSONResponse(
            status_code=e.status_code,
            content=jsonable_encoder({"error": str(e)}),
        )
