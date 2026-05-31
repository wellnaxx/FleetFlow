from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from src.adapters.driven.persistence.database.errors import DatabaseError
from src.application.exceptions.application_errors import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from src.application.exceptions.world_state_errors import (
    WorldStateCorruptionError,
    WorldStateFileNotFoundError,
    WorldStatePersistenceError,
    WorldStateRuntimeSwapError,
)
from src.domain.exceptions import (
    BusinessRuleViolationError,
    DomainConflictError,
    DomainValidationError,
    EntityNotFoundError,
)


def register_exception_handlers(app: FastAPI) -> None:
    """Register global HTTP exception handlers on a FastAPI app."""
    app.add_exception_handler(AuthenticationError, authentication_error_handler)
    app.add_exception_handler(BusinessRuleViolationError, business_rule_violation_error_handler)
    app.add_exception_handler(ConflictError, conflict_error_handler)
    app.add_exception_handler(DatabaseError, database_error_handler)
    app.add_exception_handler(DomainConflictError, domain_conflict_error_handler)
    app.add_exception_handler(DomainValidationError, domain_validation_error_handler)
    app.add_exception_handler(EntityNotFoundError, entity_not_found_error_handler)
    app.add_exception_handler(NotFoundError, not_found_error_handler)
    app.add_exception_handler(PermissionError, permission_error_handler)
    app.add_exception_handler(ValidationError, validation_error_handler)
    app.add_exception_handler(WorldStateCorruptionError, world_state_corruption_error_handler)
    app.add_exception_handler(WorldStateFileNotFoundError, world_state_file_not_found_error_handler)
    app.add_exception_handler(WorldStatePersistenceError, world_state_persistence_error_handler)
    app.add_exception_handler(WorldStateRuntimeSwapError, world_state_runtime_swap_error_handler)


async def permission_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"detail": str(exc)})


async def database_error_handler(_request: Request, _exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Database operation failed."},
    )


async def authentication_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": str(exc)})


async def conflict_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": str(exc)})


async def not_found_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)})


async def validation_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(exc)})


async def world_state_corruption_error_handler(
    _request: Request, _exc: Exception
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST, content={"detail": "World state snapshot is malformed."}
    )


async def world_state_file_not_found_error_handler(
    _request: Request, _exc: Exception
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": "World state snapshot not found."},
    )


async def world_state_persistence_error_handler(
    _request: Request, _exc: Exception
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": "World state persistence failed."}
    )


async def world_state_runtime_swap_error_handler(
    _request: Request, _exc: Exception
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "World state persistence failed."},
    )


async def business_rule_violation_error_handler(
    _request: Request, exc: Exception
) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": str(exc)})


async def domain_conflict_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": str(exc)})


async def domain_validation_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(exc)})


async def entity_not_found_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)})
