import unittest
from datetime import datetime
from unittest.mock import MagicMock, call, patch

from src.adapters.driven.persistence.database.queries import QUERIES
from src.adapters.driven.persistence.database.world_state_importer import PostgresWorldStateImporter
from src.application.dto.reconciled_world_dto import ReconciledWorld
from src.application.dto.truck_binding_dto import TruckBinding
from src.application.dto.world_state_snapshot_dto import CountersSnapshot
from src.domain.entities.customer import Customer
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.entities.truck import Truck
from src.domain.enums.item_status import ItemStatus
from src.domain.enums.route_status import RouteStatus
from src.domain.enums.truck_status import TruckStatus
from src.domain.value_objects.contact_info import ContactInfo
from src.domain.value_objects.location_code import LocationCode

MODULE = "src.adapters.driven.persistence.database.world_state_importer"


class PostgresWorldStateImporterTests(unittest.TestCase):
    @patch(f"{MODULE}.transaction_cursor")
    @patch(f"{MODULE}.execute_write_tx")
    def test_import_world_replaces_database_state_in_one_transaction(
        self,
        execute_write_tx_mock: MagicMock,
        transaction_cursor_mock: MagicMock,
    ) -> None:
        cursor = self._transaction_cursor(transaction_cursor_mock)
        departure = datetime(2026, 5, 14, 9, 0)
        expected_arrival = datetime(2026, 5, 14, 13, 0)
        customer = Customer(ContactInfo("Alice Example", "alice@example.com", "0412345678"), customer_id=7)
        route = DeliveryRoute("SYD", "MEL", departure_time=departure, route_id=21)
        route.status = RouteStatus.SCHEDULED
        truck = Truck(vehicle_id=1001, name="Scania", capacity=42000, max_range=8000)
        route.truck = truck
        package = DeliveryPackage("SYD", "MEL", 12.5, customer, package_id=11)
        package.route = route
        package.status = ItemStatus.IN_PROGRESS
        package.current_location = "SYD"
        package.expected_arrival = expected_arrival
        binding = TruckBinding(
            truck=truck,
            route=route,
            status=TruckStatus.ON_THE_WAY,
            current_location=LocationCode("SYD"),
            busy_from=departure,
            busy_until=expected_arrival,
            in_transit_to=LocationCode("MEL"),
        )
        world = ReconciledWorld(
            customers={customer.customer_id: customer},
            routes={route.route_id: route},
            packages={package.package_id: package},
            counters=CountersSnapshot(8, 12, 22),
            truck_bindings=(binding,),
        )

        PostgresWorldStateImporter().import_world(world)

        transaction_cursor_mock.assert_called_once_with()
        execute_write_tx_mock.assert_has_calls(
            [
                call(cursor, QUERIES.world_state.clear_world),
                call(
                    cursor,
                    QUERIES.customers.add_snapshot,
                    (7, "Alice Example", "alice@example.com", "0412345678"),
                ),
                call(
                    cursor,
                    QUERIES.routes.add_snapshot,
                    (21, departure, RouteStatus.SCHEDULED.value, 1001),
                ),
                call(cursor, QUERIES.routes.add_stop, (21, 0, "SYD")),
                call(cursor, QUERIES.routes.add_stop, (21, 1, "MEL")),
                call(
                    cursor,
                    QUERIES.packages.add_snapshot,
                    (11, "SYD", "MEL", 12.5, ItemStatus.IN_PROGRESS.value, "SYD", expected_arrival, 7, 21),
                ),
                call(
                    cursor,
                    QUERIES.trucks.update_state,
                    (TruckStatus.ON_THE_WAY.value, "SYD", departure, expected_arrival, "MEL", 1001),
                ),
                call(cursor, QUERIES.world_state.reset_customer_sequence, (8,)),
                call(cursor, QUERIES.world_state.reset_route_sequence, (22,)),
                call(cursor, QUERIES.world_state.reset_package_sequence, (12,)),
            ]
        )
        self.assertEqual(execute_write_tx_mock.call_count, 10)

    @patch(f"{MODULE}.transaction_cursor")
    @patch(f"{MODULE}.execute_write_tx")
    def test_import_world_handles_empty_world(
        self,
        execute_write_tx_mock: MagicMock,
        transaction_cursor_mock: MagicMock,
    ) -> None:
        cursor = self._transaction_cursor(transaction_cursor_mock)
        world = ReconciledWorld(
            customers={},
            routes={},
            packages={},
            counters=CountersSnapshot(1, 1, 1),
            truck_bindings=(),
        )

        PostgresWorldStateImporter().import_world(world)

        execute_write_tx_mock.assert_has_calls(
            [
                call(cursor, QUERIES.world_state.clear_world),
                call(cursor, QUERIES.world_state.reset_customer_sequence, (1,)),
                call(cursor, QUERIES.world_state.reset_route_sequence, (1,)),
                call(cursor, QUERIES.world_state.reset_package_sequence, (1,)),
            ]
        )
        self.assertEqual(execute_write_tx_mock.call_count, 4)

    @patch(f"{MODULE}.transaction_cursor")
    @patch(f"{MODULE}.execute_write_tx")
    def test_import_world_persists_unassigned_routes_packages_and_free_trucks(
        self,
        execute_write_tx_mock: MagicMock,
        transaction_cursor_mock: MagicMock,
    ) -> None:
        cursor = self._transaction_cursor(transaction_cursor_mock)
        customer = Customer(ContactInfo("Alice Example"), customer_id=7)
        route = DeliveryRoute("SYD", "MEL", route_id=21)
        package = DeliveryPackage("SYD", "MEL", 12.5, customer, package_id=11)
        truck = Truck(vehicle_id=1001, name="Scania", capacity=42000, max_range=8000)
        binding = TruckBinding(
            truck=truck,
            route=None,
            status=TruckStatus.FREE,
            current_location=None,
            busy_from=None,
            busy_until=None,
            in_transit_to=None,
        )
        world = ReconciledWorld(
            customers={customer.customer_id: customer},
            routes={route.route_id: route},
            packages={package.package_id: package},
            counters=CountersSnapshot(8, 12, 22),
            truck_bindings=(binding,),
        )

        PostgresWorldStateImporter().import_world(world)

        execute_write_tx_mock.assert_has_calls(
            [
                call(cursor, QUERIES.routes.add_snapshot, (21, None, RouteStatus.PLANNED.value, None)),
                call(
                    cursor,
                    QUERIES.packages.add_snapshot,
                    (11, "SYD", "MEL", 12.5, ItemStatus.TODO.value, "SYD", None, 7, None),
                ),
                call(
                    cursor,
                    QUERIES.trucks.update_state,
                    (TruckStatus.FREE.value, None, None, None, None, 1001),
                ),
            ],
            any_order=True,
        )

    @patch(f"{MODULE}.transaction_cursor")
    @patch(f"{MODULE}.execute_write_tx")
    def test_import_world_persists_partial_package_route_id(
        self,
        execute_write_tx_mock: MagicMock,
        transaction_cursor_mock: MagicMock,
    ) -> None:
        cursor = self._transaction_cursor(transaction_cursor_mock)
        customer = Customer(ContactInfo("Alice Example"), customer_id=7)
        route = DeliveryRoute("SYD", "MEL", route_id=21)
        package = DeliveryPackage("SYD", "MEL", 12.5, customer, package_id=11, route_id=21)
        world = ReconciledWorld(
            customers={customer.customer_id: customer},
            routes={route.route_id: route},
            packages={package.package_id: package},
            counters=CountersSnapshot(8, 12, 22),
            truck_bindings=(),
        )

        PostgresWorldStateImporter().import_world(world)

        execute_write_tx_mock.assert_any_call(
            cursor,
            QUERIES.packages.add_snapshot,
            (11, "SYD", "MEL", 12.5, ItemStatus.TODO.value, "SYD", None, 7, 21),
        )

    @patch(f"{MODULE}.transaction_cursor")
    @patch(f"{MODULE}.execute_write_tx")
    def test_import_world_propagates_database_errors(
        self,
        execute_write_tx_mock: MagicMock,
        transaction_cursor_mock: MagicMock,
    ) -> None:
        self._transaction_cursor(transaction_cursor_mock)
        execute_write_tx_mock.side_effect = RuntimeError("database failed")
        world = ReconciledWorld(
            customers={},
            routes={},
            packages={},
            counters=CountersSnapshot(1, 1, 1),
            truck_bindings=(),
        )

        with self.assertRaises(RuntimeError) as ctx:
            PostgresWorldStateImporter().import_world(world)

        self.assertEqual(str(ctx.exception), "database failed")
        self.assertEqual(execute_write_tx_mock.call_count, 1)

    def _transaction_cursor(self, transaction_cursor_mock: MagicMock) -> MagicMock:
        cursor = MagicMock()
        transaction_cursor_mock.return_value.__enter__.return_value = cursor
        return cursor
