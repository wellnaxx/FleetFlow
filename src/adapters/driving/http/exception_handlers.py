from fastapi import Request, status
from fastapi.responses import JSONResponse


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
    _request: Request, exc: Exception
) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)})


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
        content={"detail": "World state runtime swap failed."},
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
