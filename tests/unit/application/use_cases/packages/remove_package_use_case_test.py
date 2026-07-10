import unittest
from datetime import datetime
from unittest.mock import MagicMock

from src.application.exceptions.application_errors import NotFoundError
from src.application.use_cases.packages.remove_package import RemovePackageUseCase
from src.domain.entities.customer import Customer
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.enums.package_detachment_reasons import PackageDetachmentReason
from src.domain.events.package_events import PackageRemoved
from src.domain.exceptions import DomainConflictError, EntityNotFoundError
from src.domain.value_objects.contact_info import ContactInfo
from src.domain.value_objects.location_code import LocationCode
from tests.unit.application.use_cases.authz_helpers import manager_authz


class RemovePackageUseCase_Should(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_packages = MagicMock()
        self.unit_of_work = MagicMock()
        self.unit_of_work.__enter__.return_value = self.unit_of_work
        self.unit_of_work.__exit__.return_value = False
        self.now = datetime(2025, 10, 1, 9, 0)
        self.use_case = RemovePackageUseCase(
            self.mock_packages,
            self.unit_of_work,
            manager_authz(),
            clock=lambda: self.now,
        )

    def test_raises_when_package_not_found(self) -> None:
        self.mock_packages.get_by_id.return_value = None

        with self.assertRaises(NotFoundError) as ctx:
            self.use_case.execute(42)

        self.assertIn("Package with ID 42 not found", str(ctx.exception))
        self.mock_packages.get_by_id.assert_called_once_with(42)
        self.unit_of_work.__enter__.assert_not_called()
        self.unit_of_work.packages.remove.assert_not_called()

    def test_removes_package_without_route(self) -> None:
        package = MagicMock()
        package.package_id = 42
        package.route = None
        package.route_id = None
        self.mock_packages.get_by_id.return_value = package

        result = self.use_case.execute(42)

        self.assertIs(result.package, package)
        self.assertIs(result.customer, package.customer)
        self.assertIsNone(result.route)
        self.mock_packages.get_by_id.assert_called_once_with(42)
        package.customer.remove_package.assert_called_once_with(package)
        self.unit_of_work.packages.remove.assert_called_once_with(42)
        self.unit_of_work.commit.assert_called_once_with()

    def test_detaches_from_route_before_removal(self) -> None:
        route = MagicMock()
        package = MagicMock()
        package.package_id = 42
        package.route = route
        package.route_id = 7
        self.mock_packages.get_by_id.return_value = package

        result = self.use_case.execute(42)

        self.assertIs(result.package, package)
        self.assertIs(result.customer, package.customer)
        self.assertIs(result.route, route)
        self.mock_packages.get_by_id.assert_called_once_with(42)
        route.detach_package.assert_called_once_with(
            package,
            reason=PackageDetachmentReason.PACKAGE_REMOVED,
            occurred_at=self.now,
        )
        package.customer.remove_package.assert_called_once_with(package)
        self.unit_of_work.packages.remove.assert_called_once_with(42)
        self.unit_of_work.commit.assert_called_once_with()

    def test_removal_event_preserves_pre_detach_route_id(self) -> None:
        customer = Customer(ContactInfo("Dan", "dan@e.com", "0484568777"), customer_id=1)
        package = DeliveryPackage(
            start_location=LocationCode("SYD"),
            end_location=LocationCode("BRI"),
            weight=500,
            customer=customer,
            package_id=42,
        )
        customer.add_package(package)
        route = DeliveryRoute(LocationCode("SYD"), LocationCode("BRI"), route_id=7)
        route.assign_package(package, occurred_at=self.now)
        package.clear_events()
        self.mock_packages.get_by_id.return_value = package

        result = self.use_case.execute(42)

        self.assertIs(result.package, package)
        self.assertIs(result.customer, customer)
        self.assertIs(result.route, route)
        self.assertIsNone(package.route_id)
        self.assertNotIn(package, route.packages)
        self.assertNotIn(package, customer.delivery_packages)
        self.assertEqual(len(package.pending_events), 1)
        event = package.pending_events[0]
        self.assertIsInstance(event, PackageRemoved)
        assert isinstance(event, PackageRemoved)
        self.assertEqual(event.package_id, 42)
        self.assertEqual(event.customer_id, 1)
        self.assertEqual(event.previous_route_id, 7)
        self.assertEqual(event.previous_location, LocationCode("SYD"))
        self.assertEqual(event.occurred_at, self.now)

    def test_propagates_customer_unlink_error(self) -> None:
        package = MagicMock()
        package.package_id = 42
        package.route = None
        package.route_id = None
        package.customer.remove_package.side_effect = EntityNotFoundError("customer unlink failed")
        self.mock_packages.get_by_id.return_value = package

        with self.assertRaises(DomainConflictError) as ctx:
            self.use_case.execute(42)

        self.assertIn("customer unlink failed", str(ctx.exception))
        package.customer.remove_package.assert_called_once_with(package)
        self.unit_of_work.packages.remove.assert_not_called()

    def test_propagates_detach_error(self) -> None:
        route = MagicMock()
        route.detach_package.side_effect = EntityNotFoundError("Package is not assigned to this route")

        package = MagicMock()
        package.package_id = 42
        package.route = route
        package.route_id = 7
        self.mock_packages.get_by_id.return_value = package

        with self.assertRaises(DomainConflictError) as ctx:
            self.use_case.execute(42)

        self.assertIn("Package is not assigned to this route", str(ctx.exception))
        route.detach_package.assert_called_once_with(
            package,
            reason=PackageDetachmentReason.PACKAGE_REMOVED,
            occurred_at=self.now,
        )
        package.customer.remove_package.assert_not_called()
        self.unit_of_work.packages.remove.assert_not_called()

    def test_rejects_partially_hydrated_assigned_package(self) -> None:
        package = MagicMock()
        package.package_id = 42
        package.route = None
        package.route_id = 7
        self.mock_packages.get_by_id.return_value = package

        with self.assertRaises(DomainConflictError) as ctx:
            self.use_case.execute(42)

        self.assertIn("Package 42 is assigned to route 7, but route is not hydrated.", str(ctx.exception))
        package.customer.remove_package.assert_not_called()
        self.unit_of_work.packages.remove.assert_not_called()

    def test_restores_links_state_and_events_when_persistence_fails(self) -> None:
        route = MagicMock()
        customer = MagicMock()
        package = MagicMock()
        package.package_id = 42
        package.route = route
        package.route_id = 7
        package.customer = customer
        package_snapshot = MagicMock()
        package.snapshot_state.return_value = package_snapshot
        package.event_checkpoint.return_value = 3
        self.mock_packages.get_by_id.return_value = package
        self.unit_of_work.packages.remove.side_effect = RuntimeError("write failed")

        with self.assertRaisesRegex(RuntimeError, "write failed"):
            self.use_case.execute(42)

        package.restore_state.assert_called_once_with(package_snapshot)
        package.restore_event_checkpoint.assert_called_once_with(3)
        route.restore_package_link.assert_called_once_with(package)
        route.restore_event_checkpoint.assert_called_once_with(route.event_checkpoint.return_value)
        customer.restore_package_link.assert_called_once_with(package)
        self.unit_of_work.commit.assert_not_called()
