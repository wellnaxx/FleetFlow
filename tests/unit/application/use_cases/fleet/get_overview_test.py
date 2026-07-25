"""Tests for the fleet-overview application use case."""

import unittest
from datetime import datetime
from typing import cast
from unittest.mock import MagicMock

from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.authorization_operations import AuthorizationOperation
from src.application.events.auth_events import AuthorizationDenied
from src.application.exceptions.application_errors import ValidationError
from src.application.results.fleet_overview import FleetOverview
from src.application.services.authorization_service import AuthorizationService
from src.application.use_cases.fleet.get_overview import GetFleetOverviewUseCase
from src.domain.enums.auth import Permission
from src.ports.output.fleet_overview_query import FleetOverviewQueryPort
from tests.unit.application.use_cases.authz_helpers import employee_authz, manager_authz, principal

GENERATED_AT = datetime(2030, 1, 1, 12, 0)


class GetFleetOverviewUseCaseShould(unittest.TestCase):
    """Validate authorization, clock ownership, delegation, and failures."""

    def setUp(self) -> None:
        """Create a permitted use case with deterministic collaborators."""
        self.query = MagicMock(spec=FleetOverviewQueryPort)
        self.clock = MagicMock(return_value=GENERATED_AT)
        self.overview = cast(FleetOverview, MagicMock(spec=FleetOverview))
        self.query.get_overview.return_value = self.overview
        self.use_case = GetFleetOverviewUseCase(
            self.query,
            employee_authz(),
            clock=self.clock,
        )

    def test_uses_default_limit_and_one_clock_value(self) -> None:
        """Use one generation timestamp and the documented default limit."""
        result = self.use_case.execute()

        self.assertIs(result, self.overview)
        self.clock.assert_called_once_with()
        self.query.get_overview.assert_called_once_with(
            generated_at=GENERATED_AT,
            active_route_limit=10,
        )

    def test_delegates_explicit_limit(self) -> None:
        """Pass caller-selected limits to the overview query unchanged."""
        result = self.use_case.execute(active_route_limit=25)

        self.assertIs(result, self.overview)
        self.query.get_overview.assert_called_once_with(
            generated_at=GENERATED_AT,
            active_route_limit=25,
        )

    def test_allows_employee_and_manager_roles(self) -> None:
        """Honor the permission granted to both current application roles."""
        for authz in (employee_authz(), manager_authz()):
            with self.subTest(role=authz.current_user.role if authz.current_user else None):
                query = MagicMock(spec=FleetOverviewQueryPort)
                query.get_overview.return_value = self.overview
                clock = MagicMock(return_value=GENERATED_AT)
                use_case = GetFleetOverviewUseCase(query, authz, clock=clock)

                self.assertIs(use_case.execute(), self.overview)
                clock.assert_called_once_with()

    def test_records_unauthenticated_denial_without_querying(self) -> None:
        """Record the fleet target and required permission before rejecting."""
        use_case = GetFleetOverviewUseCase(
            self.query,
            AuthorizationService(None),
            clock=self.clock,
        )

        with self.assertRaisesRegex(PermissionError, "Unauthenticated"):
            use_case.execute()

        self.query.get_overview.assert_not_called()
        self.clock.assert_called_once_with()
        event = self._only_denial(use_case)
        self.assertEqual(event.occurred_at, GENERATED_AT)
        self.assertIs(event.attempted_operation, AuthorizationOperation.FLEET_OVERVIEW_VIEW)
        self.assertIs(event.target_resource_type, AuditResourceType.FLEET)
        self.assertIsNone(event.target_resource_id)
        self.assertEqual(event.required_permissions, (Permission.FLEET_OVERVIEW_VIEW,))

    def test_records_missing_permission_denial_without_querying(self) -> None:
        """Record denial metadata when an authenticated principal lacks access."""
        authz = MagicMock(spec=AuthorizationService)
        authz.current_user = principal(3, "restricted")
        authz.has.return_value = False
        use_case = GetFleetOverviewUseCase(self.query, authz, clock=self.clock)

        with self.assertRaisesRegex(PermissionError, "FLEET_OVERVIEW_VIEW"):
            use_case.execute()

        authz.has.assert_called_once_with(Permission.FLEET_OVERVIEW_VIEW)
        self.query.get_overview.assert_not_called()
        event = self._only_denial(use_case)
        self.assertEqual(event.required_permissions, (Permission.FLEET_OVERVIEW_VIEW,))

    def test_translates_query_type_and_value_errors_to_validation_error(self) -> None:
        """Expose query-contract failures through the application exception API."""
        for error in (
            TypeError("invalid limit"),
            ValueError("limit outside range"),
        ):
            with self.subTest(error=error):
                self.query.reset_mock()
                self.clock.reset_mock()
                self.query.get_overview.side_effect = error

                with self.assertRaisesRegex(ValidationError, str(error)) as raised:
                    self.use_case.execute(active_route_limit=101)

                self.assertIs(raised.exception.__cause__, error)
                self.clock.assert_called_once_with()
                self.query.get_overview.assert_called_once_with(
                    generated_at=GENERATED_AT,
                    active_route_limit=101,
                )

    def test_translates_clock_type_and_value_errors_without_querying(self) -> None:
        """Translate invalid clock values before persistence can be queried."""
        for error in (
            TypeError("clock failed"),
            ValueError("invalid business time"),
        ):
            with self.subTest(error=error):
                self.query.reset_mock()
                self.clock.reset_mock()
                self.clock.side_effect = error

                with self.assertRaisesRegex(ValidationError, str(error)) as raised:
                    self.use_case.execute()

                self.assertIs(raised.exception.__cause__, error)
                self.query.get_overview.assert_not_called()

        self.clock.side_effect = None

    def test_propagates_non_validation_query_failures(self) -> None:
        """Leave operational failures unchanged for driving adapters to map."""
        error = RuntimeError("database unavailable")
        self.query.get_overview.side_effect = error

        with self.assertRaisesRegex(RuntimeError, "database unavailable") as raised:
            self.use_case.execute()

        self.assertIs(raised.exception, error)

    @staticmethod
    def _only_denial(use_case: GetFleetOverviewUseCase) -> AuthorizationDenied:
        """Return the single authorization-denied event recorded by a use case."""
        events = use_case.pending_events
        if len(events) != 1 or not isinstance(events[0], AuthorizationDenied):
            raise AssertionError(f"Expected one AuthorizationDenied event, got {events!r}.")
        return events[0]
