import unittest
from datetime import datetime
from typing import cast
from unittest.mock import MagicMock, call

from src.application.commands.routes.remove_route import RemoveRouteCommand
from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.authorization_operations import AuthorizationOperation
from src.application.eventing.recorder_scope import bind_event_recorder_scope
from src.application.events.auth_events import AuthorizationDenied
from src.application.exceptions.application_errors import NotFoundError
from src.application.services.authorization_service import AuthorizationService
from src.application.use_cases.routes.remove_route import RemoveRouteUseCase
from src.domain.entities.customer import Customer
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.entities.truck import Truck
from src.domain.enums.package_detachment_reasons import PackageDetachmentReason
from src.domain.enums.truck_model import TruckModel
from src.domain.enums.truck_release_reasons import TruckReleaseReason
from src.domain.enums.truck_status import TruckStatus
from src.domain.events.route_events import PackageAssignedToRoute, RouteRemoved
from src.domain.value_objects.contact_info import ContactInfo
from tests.unit.application.use_cases.authz_helpers import manager_authz


class RemoveRouteUseCase_Should(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_routes = MagicMock()
        self.mock_uow_routes = MagicMock()
        self.mock_uow_packages = MagicMock()
        self.mock_uow_trucks = MagicMock()
        self.mock_unit_of_work = MagicMock()
        self.mock_unit_of_work.__enter__.return_value = self.mock_unit_of_work
        self.mock_unit_of_work.__exit__.return_value = False
        self.mock_unit_of_work.routes = self.mock_uow_routes
        self.mock_unit_of_work.packages = self.mock_uow_packages
        self.mock_unit_of_work.trucks = self.mock_uow_trucks
        self.now = datetime(2025, 10, 1, 9, 0)
        self.use_case = RemoveRouteUseCase(
            self.mock_routes,
            self.mock_unit_of_work,
            manager_authz(),
            clock=lambda: self.now,
        )

    def test_raises_when_route_not_found(self) -> None:
        self.mock_routes.get_by_id.return_value = None

        with self.assertRaises(NotFoundError) as ctx:
            self.use_case.execute(RemoveRouteCommand(route_id=42))

        self.assertIn("Route with ID 42 not found", str(ctx.exception))
        self.mock_routes.get_by_id.assert_called_once_with(42)
        self.mock_routes.remove.assert_not_called()
        self.mock_uow_packages.update_state.assert_not_called()
        self.mock_uow_trucks.update_state.assert_not_called()
        self.mock_unit_of_work.__enter__.assert_not_called()
        self.mock_unit_of_work.commit.assert_not_called()

    def test_removes_route_without_truck(self) -> None:
        route = MagicMock()
        route.route_id = 42
        route.truck = None
        route.packages = []
        self.mock_routes.get_by_id.return_value = route

        result = self.use_case.execute(RemoveRouteCommand(route_id=42))

        self.assertIs(result, route)
        self.mock_routes.get_by_id.assert_called_once_with(42)
        route.release_truck.assert_called_once_with(
            force=True,
            reason=TruckReleaseReason.ROUTE_REMOVED,
            occurred_at=self.now,
        )
        self.mock_routes.remove.assert_not_called()
        self.mock_uow_routes.remove.assert_called_once_with(42)
        self.mock_uow_packages.update_state.assert_not_called()
        self.mock_uow_trucks.update_state.assert_not_called()
        self.mock_unit_of_work.commit.assert_called_once_with()

    def test_releases_truck_before_removal(self) -> None:
        truck = MagicMock()
        route = MagicMock()
        route.route_id = 42
        route.truck = truck
        route.packages = []
        self.mock_routes.get_by_id.return_value = route

        result = self.use_case.execute(RemoveRouteCommand(route_id=42))

        self.assertIs(result, route)
        route.release_truck.assert_called_once_with(
            force=True,
            reason=TruckReleaseReason.ROUTE_REMOVED,
            occurred_at=self.now,
        )
        self.mock_routes.remove.assert_not_called()
        self.mock_uow_packages.update_state.assert_not_called()
        self.mock_uow_trucks.update_state.assert_called_once_with(truck)
        self.mock_uow_routes.remove.assert_called_once_with(42)
        self.mock_unit_of_work.commit.assert_called_once_with()

    def test_release_error_stops_removal(self) -> None:
        route = MagicMock()
        route.route_id = 42
        route.packages = []
        route.release_truck.side_effect = RuntimeError("truck release failed")
        self.mock_routes.get_by_id.return_value = route

        with self.assertRaises(RuntimeError) as ctx:
            self.use_case.execute(RemoveRouteCommand(route_id=42))

        self.assertIn("truck release failed", str(ctx.exception))
        route.release_truck.assert_called_once_with(
            force=True,
            reason=TruckReleaseReason.ROUTE_REMOVED,
            occurred_at=self.now,
        )
        self.mock_routes.remove.assert_not_called()
        self.mock_uow_packages.update_state.assert_not_called()
        self.mock_uow_trucks.update_state.assert_not_called()
        self.mock_unit_of_work.__enter__.assert_not_called()
        self.mock_unit_of_work.commit.assert_not_called()

    def test_detaches_assigned_packages_before_removal(self) -> None:
        package1 = MagicMock()
        package2 = MagicMock()
        route = MagicMock()
        route.route_id = 42
        route.truck = None
        route.packages = [package1, package2]
        self.mock_routes.get_by_id.return_value = route

        self.use_case.execute(RemoveRouteCommand(route_id=42))

        route.detach_package.assert_any_call(
            package1,
            reason=PackageDetachmentReason.ROUTE_REMOVED,
            occurred_at=self.now,
        )
        route.detach_package.assert_any_call(
            package2,
            reason=PackageDetachmentReason.ROUTE_REMOVED,
            occurred_at=self.now,
        )
        self.assertEqual(route.detach_package.call_count, 2)
        self.mock_uow_packages.update_state.assert_has_calls([call(package1), call(package2)], any_order=True)
        self.mock_uow_trucks.update_state.assert_not_called()
        route.release_truck.assert_called_once_with(
            force=True,
            reason=TruckReleaseReason.ROUTE_REMOVED,
            occurred_at=self.now,
        )
        self.mock_routes.remove.assert_not_called()
        self.mock_uow_routes.remove.assert_called_once_with(42)
        self.mock_unit_of_work.commit.assert_called_once_with()

    def test_detach_error_stops_removal(self) -> None:
        package = MagicMock()
        route = MagicMock()
        route.route_id = 42
        route.truck = None
        route.packages = [package]
        route.detach_package.side_effect = ValueError("detach failed")
        self.mock_routes.get_by_id.return_value = route

        with self.assertRaises(ValueError) as ctx:
            self.use_case.execute(RemoveRouteCommand(route_id=42))

        self.assertIn("detach failed", str(ctx.exception))
        route.detach_package.assert_called_once_with(
            package,
            reason=PackageDetachmentReason.ROUTE_REMOVED,
            occurred_at=self.now,
        )
        self.mock_uow_packages.update_state.assert_not_called()
        self.mock_uow_trucks.update_state.assert_not_called()
        self.mock_routes.remove.assert_not_called()
        self.mock_unit_of_work.__enter__.assert_not_called()
        self.mock_unit_of_work.commit.assert_not_called()

    def test_success_records_route_removed_with_pre_removal_links(self) -> None:
        customer = Customer(customer_id=7, contact=ContactInfo(name="Alice"))
        package = DeliveryPackage("SYD", "MEL", 12.5, customer, 11)
        route = DeliveryRoute("SYD", "MEL", route_id=42)
        truck = Truck(1001, TruckModel.SCANIA, 42000, 8000)
        truck.current_location = "SYD"
        route.assign_package(package, occurred_at=self.now)
        route.assign_truck(truck, occurred_at=self.now)
        route.clear_events()
        self.mock_routes.get_by_id.return_value = route

        removed = self.use_case.execute(RemoveRouteCommand(route_id=42))

        self.assertIs(removed, route)
        self.assertEqual(route.packages, ())
        self.assertIsNone(route.truck)
        event = route.pending_events[-1]
        self.assertIsInstance(event, RouteRemoved)
        assert isinstance(event, RouteRemoved)
        self.assertEqual(event.route_id, 42)
        self.assertEqual(event.detached_package_ids, (11,))
        self.assertEqual(event.released_truck_id, 1001)
        self.assertEqual(event.occurred_at, self.now)

    def test_restores_packages_and_truck_when_persistence_fails(self) -> None:
        customer = Customer(customer_id=7, contact=ContactInfo(name="Alice"))
        package = DeliveryPackage("SYD", "MEL", 12.5, customer, 11)
        route = DeliveryRoute("SYD", "MEL", departure_time=datetime(2026, 5, 2, 9, 0), route_id=42)
        truck = Truck(1001, TruckModel.SCANIA, 42000, 8000)
        truck.current_location = "SYD"
        route.assign_package(
            package,
            now=datetime(2026, 5, 2, 8, 0),
            occurred_at=datetime(2026, 5, 2, 8, 0),
        )
        route.truck = truck
        truck.assign(route)
        error = RuntimeError("delete failed")
        self.mock_routes.get_by_id.return_value = route
        self.mock_uow_routes.remove.side_effect = error

        with self.assertRaises(RuntimeError) as ctx:
            self.use_case.execute(RemoveRouteCommand(route_id=42))

        self.assertIs(ctx.exception, error)
        self.assertEqual(route.packages, (package,))
        self.assertIs(package.route, route)
        self.assertIs(route.truck, truck)
        self.assertIs(truck.route, route)
        self.assertEqual(truck.status, TruckStatus.ON_THE_WAY)
        self.assertEqual(len(route.pending_events), 1)
        self.assertIsInstance(route.pending_events[0], PackageAssignedToRoute)
        self.assertFalse(any(isinstance(event, RouteRemoved) for event in route.pending_events))

    def test_tracks_removed_route_in_execution_scope(self) -> None:
        route = MagicMock()
        route.route_id = 42
        route.truck = None
        route.packages = []
        self.mock_routes.get_by_id.return_value = route

        with bind_event_recorder_scope() as scope:
            result = self.use_case.execute(RemoveRouteCommand(route_id=42))

        self.assertIs(result, route)
        self.assertEqual(scope.event_recorders(), (scope, route))

    def test_records_targeted_authorization_denial_before_repository_access(self) -> None:
        use_case = RemoveRouteUseCase(
            self.mock_routes,
            self.mock_unit_of_work,
            AuthorizationService(None),
            clock=lambda: self.now,
        )

        with self.assertRaisesRegex(PermissionError, "Unauthenticated"):
            use_case.execute(RemoveRouteCommand(route_id=42))

        self.mock_routes.get_by_id.assert_not_called()
        self.mock_unit_of_work.__enter__.assert_not_called()
        self.assertEqual(len(use_case.pending_events), 1)
        event = cast(AuthorizationDenied, use_case.pending_events[0])
        self.assertIsInstance(event, AuthorizationDenied)
        self.assertIs(event.attempted_operation, AuthorizationOperation.ROUTE_REMOVE)
        self.assertIs(event.target_resource_type, AuditResourceType.ROUTE)
        self.assertEqual(event.target_resource_id, "42")
