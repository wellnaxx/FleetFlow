import unittest
from datetime import datetime
from typing import cast
from unittest.mock import MagicMock

from src.application.commands.routes.create_route import CreateRouteCommand
from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.authorization_operations import AuthorizationOperation
from src.application.eventing.recorder_scope import bind_event_recorder_scope
from src.application.events.auth_events import AuthorizationDenied
from src.application.services.authorization_service import AuthorizationService
from src.application.use_cases.routes.create_route import CreateRouteUseCase
from src.domain.exceptions import DomainValidationError
from tests.unit.application.use_cases.authz_helpers import manager_authz


class CreateRouteUseCase_Should(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_routes = MagicMock()
        self.use_case = CreateRouteUseCase(self.mock_routes, manager_authz())

    def test_creates_route_when_inputs_are_valid(self) -> None:
        departure = datetime(2025, 10, 12, 6, 0)
        fake_route = MagicMock()
        self.mock_routes.create.return_value = fake_route

        command = CreateRouteCommand(
            locations=("SYD", "MEL", "ADL"),
            departure_time=departure,
        )
        result = self.use_case.execute(command)

        self.assertIs(result, fake_route)
        self.mock_routes.create.assert_called_once_with(
            locations=("SYD", "MEL", "ADL"),
            departure_time=departure,
        )

    def test_raises_when_fewer_than_two_locations(self) -> None:
        self.mock_routes.create.side_effect = DomainValidationError("A route must have at least two locations.")

        with self.assertRaises(DomainValidationError) as ctx:
            self.use_case.execute(CreateRouteCommand(locations=("SYD",)))

        self.assertIn("at least two locations", str(ctx.exception))
        self.mock_routes.create.assert_called_once_with(
            locations=("SYD",),
            departure_time=None,
        )

    def test_raises_when_any_location_is_invalid(self) -> None:
        self.mock_routes.create.side_effect = DomainValidationError("Invalid location code: BAD.")

        with self.assertRaises(DomainValidationError) as ctx:
            self.use_case.execute(CreateRouteCommand(locations=("SYD", "BAD", "MEL")))

        self.assertIn("Invalid location code: BAD", str(ctx.exception))
        self.mock_routes.create.assert_called_once_with(
            locations=("SYD", "BAD", "MEL"),
            departure_time=None,
        )

    def test_delegates_locations_to_repository_for_validation_and_creation(self) -> None:
        fake_route = MagicMock()
        self.mock_routes.create.return_value = fake_route

        result = self.use_case.execute(CreateRouteCommand(locations=("A", "B", "C")))

        self.assertIs(result, fake_route)
        self.mock_routes.create.assert_called_once_with(
            locations=("A", "B", "C"),
            departure_time=None,
        )

    def test_records_authorization_denial_before_repository_access(self) -> None:
        use_case = CreateRouteUseCase(self.mock_routes, AuthorizationService(None))

        with self.assertRaisesRegex(PermissionError, "Unauthenticated"):
            use_case.execute(CreateRouteCommand(locations=("SYD", "MEL")))

        self.mock_routes.create.assert_not_called()
        self.assertEqual(len(use_case.pending_events), 1)
        event = cast(AuthorizationDenied, use_case.pending_events[0])
        self.assertIsInstance(event, AuthorizationDenied)
        self.assertIs(event.attempted_operation, AuthorizationOperation.ROUTE_CREATE)
        self.assertIs(event.target_resource_type, AuditResourceType.ROUTE)
        self.assertIsNone(event.target_resource_id)

    def test_tracks_persisted_route_in_execution_scope(self) -> None:
        route = MagicMock()
        self.mock_routes.create.return_value = route

        with bind_event_recorder_scope() as scope:
            result = self.use_case.execute(CreateRouteCommand(locations=("SYD", "MEL")))

        self.assertIs(result, route)
        self.assertEqual(scope.event_recorders(), (scope, route))
