import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

from src.application.services.world_state_reconciliation_service import WorldStateReconciliationService
from src.domain.entities.customer import Customer
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.entities.truck import Truck
from src.domain.enums.item_status import ItemStatus
from src.domain.enums.route_status import RouteStatus
from src.domain.enums.truck_model import TruckModel
from src.domain.enums.truck_status import TruckStatus
from src.domain.value_objects.contact_info import ContactInfo
from src.domain.value_objects.location_code import LocationCode


def _distance(_start: str, _end: str) -> int:
    return 100


class WorldStateReconciliationServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.route_map_locations = patch(
            "src.domain.entities.delivery_route.Map.get_locations",
            return_value=[LocationCode("A"), LocationCode("B"), LocationCode("C")],
        )
        self.route_map_distance = patch(
            "src.domain.entities.delivery_route.Map.get_distance",
            side_effect=_distance,
        )
        self.package_map_valid = patch(
            "src.domain.entities.delivery_package.Map.is_valid_location",
            return_value=True,
        )

        self.route_map_locations.start()
        self.route_map_distance.start()
        self.package_map_valid.start()

        self.addCleanup(self.route_map_locations.stop)
        self.addCleanup(self.route_map_distance.stop)
        self.addCleanup(self.package_map_valid.stop)

        self.reconciler = WorldStateReconciliationService()

    def make_customer(self) -> Customer:
        return Customer(
            customer_id=1,
            contact=ContactInfo(
                name="Alice",
                email="",
                phone_number="",
            ),
        )

    def test_reconcile_routes_counts_one_package_once_even_when_multiple_package_fields_change(self) -> None:
        customer = self.make_customer()

        package = DeliveryPackage(
            package_id=1,
            start_location=LocationCode("A"),
            end_location=LocationCode("C"),
            weight=5.0,
            customer=customer,
        )
        customer.add_package(package)

        route = DeliveryRoute(
            LocationCode("A"),
            LocationCode("B"),
            LocationCode("C"),
            departure_time=datetime(2025, 1, 1, 10, 0, 0),
            route_id=1,
        )
        route.restore_package_link(package)

        def arrival_time_at(city: str) -> datetime:
            return {
                LocationCode("A"): datetime(2025, 1, 1, 10, 0, 0),
                LocationCode("B"): datetime(2025, 1, 1, 11, 0, 0),
                LocationCode("C"): datetime(2025, 1, 1, 12, 0, 0),
            }[LocationCode(city)]

        with patch.object(route, "arrival_time_at") as arrival_time_at_mock:
            arrival_time_at_mock.side_effect = arrival_time_at

            summary = self.reconciler.reconcile_routes(
                routes=[route],
                now=datetime(2025, 1, 1, 11, 30, 0),
                update_trucks=False,
            )

        self.assertEqual(summary.packages_updated, 1)
        self.assertEqual(package.status, ItemStatus.IN_PROGRESS)
        self.assertEqual(package.current_location, LocationCode("B"))
        self.assertEqual(package.expected_arrival, datetime(2025, 1, 1, 12, 0, 0))
        self.assertTrue(summary.state_changed)

    def test_reconcile_routes_does_not_count_unchanged_package(self) -> None:
        customer = self.make_customer()

        package = DeliveryPackage(
            package_id=1,
            start_location=LocationCode("A"),
            end_location=LocationCode("B"),
            weight=5.0,
            customer=customer,
        )
        customer.add_package(package)

        route = DeliveryRoute(
            LocationCode("A"),
            LocationCode("B"),
            departure_time=datetime(2025, 1, 1, 10, 0, 0),
            route_id=1,
        )
        route.restore_package_link(package)

        expected_arrival = datetime(2025, 1, 1, 11, 0, 0)
        package.status = ItemStatus.DONE
        package.current_location = LocationCode("B")
        package.expected_arrival = expected_arrival
        route.status = RouteStatus.COMPLETED

        def arrival_time_at(city: str) -> datetime:
            return {
                LocationCode("A"): datetime(2025, 1, 1, 10, 0, 0),
                LocationCode("B"): expected_arrival,
            }[LocationCode(city)]

        with patch.object(route, "arrival_time_at") as arrival_time_at_mock:
            arrival_time_at_mock.side_effect = arrival_time_at

            summary = self.reconciler.reconcile_routes(
                routes=[route],
                now=datetime(2025, 1, 1, 12, 0, 0),
                update_trucks=False,
            )

        self.assertEqual(summary.packages_updated, 0)

    def test_reconcile_routes_counts_distinct_changed_packages(self) -> None:
        customer = self.make_customer()

        package_1 = DeliveryPackage(
            package_id=1,
            start_location=LocationCode("A"),
            end_location=LocationCode("B"),
            weight=5.0,
            customer=customer,
        )
        package_2 = DeliveryPackage(
            package_id=2,
            start_location=LocationCode("A"),
            end_location=LocationCode("C"),
            weight=5.0,
            customer=customer,
        )

        customer.add_package(package_1)
        customer.add_package(package_2)

        route = DeliveryRoute(
            LocationCode("A"),
            LocationCode("B"),
            LocationCode("C"),
            departure_time=datetime(2025, 1, 1, 10, 0, 0),
            route_id=1,
        )
        route.restore_package_link(package_1)
        route.restore_package_link(package_2)

        def arrival_time_at(city: str) -> datetime:
            return {
                LocationCode("A"): datetime(2025, 1, 1, 10, 0, 0),
                LocationCode("B"): datetime(2025, 1, 1, 11, 0, 0),
                LocationCode("C"): datetime(2025, 1, 1, 12, 0, 0),
            }[LocationCode(city)]

        with patch.object(route, "arrival_time_at") as arrival_time_at_mock:
            arrival_time_at_mock.side_effect = arrival_time_at

            summary = self.reconciler.reconcile_routes(
                routes=[route],
                now=datetime(2025, 1, 1, 11, 30, 0),
                update_trucks=False,
            )

        self.assertEqual(summary.packages_updated, 2)
        self.assertTrue(summary.state_changed)

    def test_reconcile_routes_counts_after_end_release_location_change_as_movement(self) -> None:
        route = DeliveryRoute(
            LocationCode("A"),
            LocationCode("B"),
            departure_time=datetime(2025, 1, 1, 10, 0, 0),
            route_id=1,
        )

        truck = Truck(
            vehicle_id=1001,
            name=TruckModel.SCANIA,
            capacity=42000,
            max_range=8000,
        )
        truck.assign(route)
        truck.current_location = LocationCode("A")
        route.truck = truck

        summary = self.reconciler.reconcile_routes(
            routes=[route],
            now=datetime(2026, 1, 1, 10, 0, 0),
            update_trucks=True,
        )

        self.assertEqual(summary.trucks_released, 1)
        self.assertEqual(summary.trucks_moved, 1)
        self.assertTrue(summary.state_changed)
        self.assertIsNone(route.truck)
        self.assertIsNone(truck.route)
        self.assertEqual(truck.status, TruckStatus.FREE)
        self.assertEqual(truck.current_location, LocationCode("B"))

    def test_reconcile_routes_counts_truck_location_change_as_movement(self) -> None:
        route = DeliveryRoute(
            LocationCode("A"),
            LocationCode("B"),
            departure_time=datetime(2099, 1, 1, 10, 0, 0),
            route_id=1,
        )

        truck = Truck(
            vehicle_id=1001,
            name=TruckModel.SCANIA,
            capacity=42000,
            max_range=8000,
        )
        truck.current_location = LocationCode("C")
        truck.assign(route)
        route.truck = truck

        summary = self.reconciler.reconcile_routes(
            routes=[route],
            now=datetime(2099, 1, 1, 9, 0, 0),
            update_trucks=True,
        )

        self.assertEqual(summary.trucks_moved, 1)
        self.assertEqual(summary.trucks_released, 0)
        self.assertEqual(truck.current_location, LocationCode("A"))
        self.assertTrue(summary.state_changed)

    def test_reconcile_routes_counts_expected_arrival_only_update_as_one_package(self) -> None:
        customer = self.make_customer()

        package = DeliveryPackage(
            package_id=1,
            start_location=LocationCode("A"),
            end_location=LocationCode("C"),
            weight=5.0,
            customer=customer,
        )
        customer.add_package(package)

        route = DeliveryRoute(
            LocationCode("A"),
            LocationCode("B"),
            LocationCode("C"),
            departure_time=datetime(2025, 1, 1, 10, 0, 0),
            route_id=1,
        )
        route.restore_package_link(package)

        package.status = ItemStatus.IN_PROGRESS
        package.current_location = LocationCode("B")
        package.expected_arrival = None
        route.status = RouteStatus.IN_PROGRESS

        def arrival_time_at(city: str) -> datetime:
            return {
                LocationCode("A"): datetime(2025, 1, 1, 10, 0, 0),
                LocationCode("B"): datetime(2025, 1, 1, 11, 0, 0),
                LocationCode("C"): datetime(2025, 1, 1, 12, 0, 0),
            }[LocationCode(city)]

        with patch.object(route, "arrival_time_at") as arrival_time_at_mock:
            arrival_time_at_mock.side_effect = arrival_time_at

            summary = self.reconciler.reconcile_routes(
                routes=[route],
                now=datetime(2025, 1, 1, 11, 30, 0),
                update_trucks=False,
            )

        self.assertEqual(summary.packages_updated, 1)
        self.assertEqual(package.status, ItemStatus.IN_PROGRESS)
        self.assertEqual(package.current_location, LocationCode("B"))
        self.assertEqual(package.expected_arrival, datetime(2025, 1, 1, 12, 0, 0))
        self.assertTrue(summary.state_changed)

    def test_reconcile_routes_final_stop_release_does_not_count_as_movement_when_location_unchanged(
        self,
    ) -> None:
        route = DeliveryRoute(
            LocationCode("A"),
            LocationCode("B"),
            departure_time=datetime(2025, 1, 1, 10, 0, 0),
            route_id=1,
        )

        truck = Truck(
            vehicle_id=1001,
            name=TruckModel.SCANIA,
            capacity=42000,
            max_range=8000,
        )
        truck.assign(route)
        truck.current_location = LocationCode("B")
        route.truck = truck

        with patch.object(route, "current_position") as current_position_mock:
            current_position_mock.return_value = SimpleNamespace(
                kind="AT_STOP",
                stop_city=LocationCode("B"),
            )

            summary = self.reconciler.reconcile_routes(
                routes=[route],
                now=route.eta_final or datetime(2025, 1, 1, 11, 0, 0),
                update_trucks=True,
            )

        self.assertEqual(summary.trucks_released, 1)
        self.assertEqual(summary.trucks_moved, 0)
        self.assertTrue(summary.state_changed)
        self.assertIsNone(route.truck)
        self.assertIsNone(truck.route)
        self.assertEqual(truck.status, TruckStatus.FREE)
        self.assertEqual(truck.current_location, LocationCode("B"))

    def test_reconcile_routes_at_stop_counts_clearing_stale_in_transit_as_movement(self) -> None:
        route = DeliveryRoute(
            LocationCode("A"),
            LocationCode("B"),
            LocationCode("C"),
            departure_time=datetime(2025, 1, 1, 10, 0, 0),
            route_id=1,
        )

        truck = Truck(
            vehicle_id=1001,
            name=TruckModel.SCANIA,
            capacity=42000,
            max_range=8000,
        )
        truck.assign(route)
        truck.current_location = LocationCode("B")
        truck.in_transit_to = LocationCode("C")
        route.truck = truck

        with patch.object(route, "current_position") as current_position_mock:
            current_position_mock.return_value = SimpleNamespace(
                kind="AT_STOP",
                stop_city=LocationCode("B"),
            )

            summary = self.reconciler.reconcile_routes(
                routes=[route],
                now=datetime(2025, 1, 1, 11, 0, 0),
                update_trucks=True,
            )

        self.assertEqual(summary.trucks_moved, 1)
        self.assertEqual(summary.trucks_released, 0)
        self.assertTrue(summary.state_changed)
        self.assertIs(route.truck, truck)
        self.assertIs(truck.route, route)
        self.assertEqual(truck.current_location, LocationCode("B"))
        self.assertIsNone(truck.in_transit_to)

    def test_reconcile_routes_does_not_mutate_truck_when_truck_updates_are_disabled(self) -> None:
        route = DeliveryRoute(
            LocationCode("A"),
            LocationCode("B"),
            departure_time=datetime(2099, 1, 1, 10, 0, 0),
            route_id=1,
        )

        truck = Truck(
            vehicle_id=1001,
            name=TruckModel.SCANIA,
            capacity=42000,
            max_range=8000,
        )

        truck.assign(route)
        route.truck = truck

        truck.current_location = LocationCode("C")
        truck.in_transit_to = LocationCode("B")

        summary = self.reconciler.reconcile_routes(
            routes=[route],
            now=datetime(2099, 1, 1, 9, 0, 0),
            update_trucks=False,
        )

        self.assertEqual(summary.trucks_moved, 0)
        self.assertEqual(summary.trucks_released, 0)
        self.assertEqual(truck.current_location, LocationCode("C"))
        self.assertEqual(truck.in_transit_to, LocationCode("B"))
        self.assertIs(truck.route, route)
        self.assertIs(route.truck, truck)
