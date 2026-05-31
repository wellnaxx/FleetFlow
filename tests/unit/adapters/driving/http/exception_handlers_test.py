import asyncio
import json
import unittest
from collections.abc import Awaitable, Callable
from typing import cast
from unittest.mock import Mock

from fastapi import Request, status
from fastapi.responses import JSONResponse

from src.adapters.driven.persistence.database.errors import DatabaseError
from src.adapters.driving.http.exception_handlers import (
    authentication_error_handler,
    business_rule_violation_error_handler,
    conflict_error_handler,
    database_error_handler,
    domain_conflict_error_handler,
    domain_validation_error_handler,
    entity_not_found_error_handler,
    not_found_error_handler,
    permission_error_handler,
    validation_error_handler,
    world_state_corruption_error_handler,
    world_state_file_not_found_error_handler,
    world_state_persistence_error_handler,
    world_state_runtime_swap_error_handler,
)
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

ExceptionHandler = Callable[[Request, Exception], Awaitable[JSONResponse]]


class HttpExceptionHandlersShould(unittest.TestCase):
    async def _call_handler(self, handler: ExceptionHandler, exc: Exception) -> JSONResponse:
        request = cast(Request, Mock(spec=Request))
        return await handler(request, exc)

    def test_map_known_exceptions_to_http_responses(self) -> None:
        cases: list[tuple[ExceptionHandler, Exception, int, str]] = [
            (
                permission_error_handler,
                PermissionError("Missing permission: ROUTE_VIEW_ALL"),
                status.HTTP_403_FORBIDDEN,
                "Missing permission: ROUTE_VIEW_ALL",
            ),
            (
                database_error_handler,
                DatabaseError("Database read failed: connection refused"),
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "Database operation failed.",
            ),
            (
                authentication_error_handler,
                AuthenticationError("Invalid credentials."),
                status.HTTP_401_UNAUTHORIZED,
                "Invalid credentials.",
            ),
            (
                conflict_error_handler,
                ConflictError("Username already exists."),
                status.HTTP_409_CONFLICT,
                "Username already exists.",
            ),
            (
                not_found_error_handler,
                NotFoundError("User not found."),
                status.HTTP_404_NOT_FOUND,
                "User not found.",
            ),
            (
                validation_error_handler,
                ValidationError("Invalid request."),
                status.HTTP_400_BAD_REQUEST,
                "Invalid request.",
            ),
            (
                world_state_corruption_error_handler,
                WorldStateCorruptionError("C:/secret/world.json contains invalid data"),
                status.HTTP_400_BAD_REQUEST,
                "World state snapshot is malformed.",
            ),
            (
                world_state_file_not_found_error_handler,
                WorldStateFileNotFoundError("World state file not found: world.json"),
                status.HTTP_404_NOT_FOUND,
                "World state snapshot not found.",
            ),
            (
                world_state_persistence_error_handler,
                WorldStatePersistenceError("C:/secret/world.json denied"),
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "World state persistence failed.",
            ),
            (
                world_state_runtime_swap_error_handler,
                WorldStateRuntimeSwapError("runtime swap failed"),
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "World state persistence failed.",
            ),
            (
                business_rule_violation_error_handler,
                BusinessRuleViolationError("Truck cannot complete route."),
                status.HTTP_409_CONFLICT,
                "Truck cannot complete route.",
            ),
            (
                domain_conflict_error_handler,
                DomainConflictError("Package is already assigned."),
                status.HTTP_409_CONFLICT,
                "Package is already assigned.",
            ),
            (
                domain_validation_error_handler,
                DomainValidationError("Route requires at least two stops."),
                status.HTTP_400_BAD_REQUEST,
                "Route requires at least two stops.",
            ),
            (
                entity_not_found_error_handler,
                EntityNotFoundError("Route 42 was not found."),
                status.HTTP_404_NOT_FOUND,
                "Route 42 was not found.",
            ),
        ]

        for handler, exc, expected_status, expected_detail in cases:
            with self.subTest(handler=handler.__name__):
                response = asyncio.run(self._call_handler(handler, exc))

                self.assertEqual(response.status_code, expected_status)
                self.assertEqual(json.loads(cast(bytes, response.body)), {"detail": expected_detail})
