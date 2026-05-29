import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.application.exceptions.application_errors import NotFoundError
from src.application.results.assign_packages_to_route_result import (
    AssignPackagesToRouteResult,
    PackageAssignmentError,
    PackageAssignmentSuccess,
)
from src.application.use_cases.routes.assign_packages_to_route import AssignPackagesToRouteUseCase
from src.domain.exceptions import DomainConflictError, DomainValidationError
from tests.unit.application.use_cases.authz_helpers import manager_authz


class AssignPackagesToRouteUseCase_Should(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_routes = MagicMock()
        self.mock_packages = MagicMock()
        self.now = datetime(2025, 10, 1, 9, 0)
        self.use_case = AssignPackagesToRouteUseCase(
            self.mock_routes,
            self.mock_packages,
            manager_authz(),
            clock=lambda: self.now,
        )

    def _make_route(self, route_id: int = 7, departure_time: datetime | None = None) -> MagicMock:
        route = MagicMock()
        route.route_id = route_id
        route.departure_time = departure_time
        return route

    def _make_package(
        self,
        package_id: int,
        *,
        end_location: str = "MEL",
        route: object | None = None,
    ) -> MagicMock:
        package = MagicMock()
        package.package_id = package_id
        package.end_location = end_location
        package.route = route
        return package

    def test_raises_when_route_not_found(self) -> None:
        self.mock_routes.get_by_id.return_value = None

        with self.assertRaises(NotFoundError) as ctx:
            self.use_case.execute(7, [8, 9])

        self.assertIn("Route with ID 7 not found.", str(ctx.exception))
        self.mock_packages.get_by_id.assert_not_called()

    def test_returns_success_for_single_package(self) -> None:
        route = self._make_route(route_id=7, departure_time=None)
        package = self._make_package(8)

        self.mock_routes.get_by_id.return_value = route
        self.mock_packages.get_by_id.return_value = package

        result = self.use_case.execute(7, [8])

        self.assertEqual(
            result,
            AssignPackagesToRouteResult(
                successes=[
                    PackageAssignmentSuccess(
                        package_id=8,
                        route_id=7,
                        eta_text="N/A (route unscheduled)",
                    )
                ],
                errors=[],
            ),
        )
        route.assign_package.assert_called_once_with(package, now=self.now)
        self.mock_packages.update_state.assert_called_once_with(package)

    def test_returns_success_for_scheduled_route_with_eta(self) -> None:
        route = self._make_route(route_id=7, departure_time=datetime(2025, 10, 1, 9, 0))
        package = self._make_package(8, end_location="MEL")
        route.arrival_time_at.return_value = datetime(2025, 10, 1, 18, 0)

        self.mock_routes.get_by_id.return_value = route
        self.mock_packages.get_by_id.return_value = package

        result = self.use_case.execute(7, [8])

        self.assertEqual(result.successes[0].eta_text, "2025-10-01 18:00")
        route.assign_package.assert_called_once_with(package, now=self.now)
        self.mock_packages.update_state.assert_called_once_with(package)
        route.arrival_time_at.assert_called_once_with("MEL")

    def test_deduplicates_package_ids(self) -> None:
        route = self._make_route(route_id=7, departure_time=None)
        package = self._make_package(8)

        self.mock_routes.get_by_id.return_value = route
        self.mock_packages.get_by_id.return_value = package

        result = self.use_case.execute(7, [8, 8, 8])

        self.assertEqual(len(result.successes), 1)
        self.assertEqual(len(result.errors), 0)
        self.mock_packages.get_by_id.assert_called_once_with(8)
        route.assign_package.assert_called_once_with(package, now=self.now)
        self.mock_packages.update_state.assert_called_once_with(package)

    def test_returns_errors_when_all_packages_missing(self) -> None:
        route = self._make_route(route_id=7, departure_time=None)
        self.mock_routes.get_by_id.return_value = route
        self.mock_packages.get_by_id.return_value = None

        result = self.use_case.execute(7, [8])

        self.assertEqual(result.successes, [])
        self.assertEqual(
            result.errors,
            [PackageAssignmentError(package_id=8, message="Package 8 not found.")],
        )
        self.mock_packages.update_state.assert_not_called()

    def test_returns_errors_when_all_packages_already_assigned(self) -> None:
        route = self._make_route(route_id=7, departure_time=None)
        other_route = SimpleNamespace(route_id=3)
        package = self._make_package(8, route=other_route)

        self.mock_routes.get_by_id.return_value = route
        self.mock_packages.get_by_id.return_value = package

        result = self.use_case.execute(7, [8])

        self.assertEqual(result.successes, [])
        self.assertEqual(
            result.errors,
            [PackageAssignmentError(package_id=8, message="Package 8 is already on route 3.")],
        )
        self.mock_packages.update_state.assert_not_called()

    def test_returns_errors_when_all_assignments_fail_on_route_validation(self) -> None:
        route = self._make_route(route_id=7, departure_time=None)
        package = self._make_package(8)
        route.assign_package.side_effect = DomainConflictError("capacity exceeded")

        self.mock_routes.get_by_id.return_value = route
        self.mock_packages.get_by_id.return_value = package

        result = self.use_case.execute(7, [8])

        self.assertEqual(result.successes, [])
        self.assertEqual(
            result.errors,
            [PackageAssignmentError(package_id=8, message="capacity exceeded")],
        )
        self.mock_packages.update_state.assert_not_called()

    def test_partial_success_returns_successes_and_errors(self) -> None:
        route = self._make_route(route_id=7, departure_time=None)
        package_ok = self._make_package(8)
        package_bad = self._make_package(9, route=SimpleNamespace(route_id=2))

        self.mock_routes.get_by_id.return_value = route
        self.mock_packages.get_by_id.side_effect = [package_ok, package_bad]

        result = self.use_case.execute(7, [8, 9])

        self.assertEqual(
            result,
            AssignPackagesToRouteResult(
                successes=[
                    PackageAssignmentSuccess(
                        package_id=8,
                        route_id=7,
                        eta_text="N/A (route unscheduled)",
                    )
                ],
                errors=[
                    PackageAssignmentError(
                        package_id=9,
                        message="Package 9 is already on route 2.",
                    )
                ],
            ),
        )
        self.mock_packages.update_state.assert_called_once_with(package_ok)

    def test_eta_falls_back_to_na_when_arrival_lookup_fails(self) -> None:
        route = self._make_route(route_id=7, departure_time=datetime(2025, 10, 1, 9, 0))
        package = self._make_package(8, end_location="MEL")
        route.arrival_time_at.side_effect = DomainValidationError("not on route")

        self.mock_routes.get_by_id.return_value = route
        self.mock_packages.get_by_id.return_value = package

        result = self.use_case.execute(7, [8])

        self.assertEqual(result.successes[0].eta_text, "N/A")
