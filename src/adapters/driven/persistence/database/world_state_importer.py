from collections.abc import Iterable

from psycopg import Cursor

from src.adapters.driven.persistence.database.executor import (
    Row,
    execute_write_tx,
    transaction_cursor,
)
from src.adapters.driven.persistence.database.queries import QUERIES
from src.application.dto.reconciled_world_dto import ReconciledWorld
from src.application.dto.truck_binding_dto import TruckBinding
from src.application.dto.world_state_snapshot_dto import CountersSnapshot
from src.domain.entities.customer import Customer
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.entities.delivery_route import DeliveryRoute


class PostgresWorldStateImporter:
    def import_world(self, reconciled_world: ReconciledWorld) -> None:
        """Import a reconciled world into the database.

        Args:
            reconciled_world: The reconciled world to import.

        Raises:
            DatabaseError: If there is an error during database operations.
        """
        with transaction_cursor() as cursor:
            self._clear_world(cursor)
            self._insert_customers(cursor, reconciled_world.customers.values())
            self._insert_routes(cursor, reconciled_world.routes.values())
            self._insert_packages(cursor, reconciled_world.packages.values())
            self._update_trucks(cursor, reconciled_world.truck_bindings)
            self._reset_sequences(cursor, reconciled_world.counters)

    def _clear_world(self, cursor: Cursor[Row]) -> None:
        """Clear the existing world state from the database.

        Args:
            cursor: Database cursor to execute deletion queries.

        Raises:
            DatabaseError: If the transaction or delete operations fail.
        """
        execute_write_tx(cursor, QUERIES.world_state.clear_world)

    def _insert_customers(self, cursor: Cursor[Row], customers: Iterable[Customer]) -> None:
        """Insert customers into the database.

        Args:
            cursor: Database cursor to execute insertion queries.
            customers: List of customers to insert.

        Raises:
            DatabaseError: If any insert operation fails.
        """
        for customer in customers:
            execute_write_tx(
                cursor,
                QUERIES.customers.add_snapshot,
                (
                    customer.customer_id,
                    customer.contact.name,
                    customer.contact.email,
                    customer.contact.phone_number,
                ),
            )

    def _insert_routes(self, cursor: Cursor[Row], routes: Iterable[DeliveryRoute]) -> None:
        """Insert routes into the database.

        Args:
            cursor: Database cursor to execute insertion queries.
            routes: List of routes to insert.

        Raises:
            DatabaseError: If any insert operation fails.
        """
        for route in routes:
            execute_write_tx(
                cursor,
                QUERIES.routes.add_snapshot,
                (
                    route.route_id,
                    route.departure_time,
                    route.status.value,
                    route.truck.vehicle_id if route.truck is not None else None,
                ),
            )

            for stop_order, location in enumerate(route.locations):
                execute_write_tx(
                    cursor,
                    QUERIES.routes.add_stop,
                    (route.route_id, stop_order, str(location)),
                )

    def _insert_packages(self, cursor: Cursor[Row], packages: Iterable[DeliveryPackage]) -> None:
        """Insert packages into the database.

        Args:
            cursor: Database cursor to execute insertion queries.
            packages: List of packages to insert.

        Raises:
            DatabaseError: If any insert operation fails.
        """
        for package in packages:
            execute_write_tx(
                cursor,
                QUERIES.packages.add_snapshot,
                (
                    package.package_id,
                    str(package.start_location),
                    str(package.end_location),
                    package.weight,
                    package.status.value,
                    str(package.current_location),
                    package.expected_arrival,
                    package.customer.customer_id,
                    package.route.route_id if package.route is not None else None,
                ),
            )

    def _update_trucks(self, cursor: Cursor[Row], truck_bindings: Iterable[TruckBinding]) -> None:
        """Update trucks in the database to match the provided state.

        Args:
            cursor: Database cursor to execute update queries.
            truck_bindings: List of truck bindings with updated state.

        Raises:
            DatabaseError: If any update operation fails.
        """
        for binding in truck_bindings:
            execute_write_tx(
                cursor,
                QUERIES.trucks.update_state,
                (
                    binding.status.value,
                    str(binding.current_location) if binding.current_location is not None else None,
                    binding.busy_from,
                    binding.busy_until,
                    str(binding.in_transit_to) if binding.in_transit_to is not None else None,
                    binding.truck.vehicle_id,
                ),
            )

    def _reset_sequences(self, cursor: Cursor[Row], counters: CountersSnapshot) -> None:
        """Reset database sequences to avoid conflicts with imported data.

        Args:
            cursor: Database cursor to execute sequence reset queries.
            counters: Snapshot of current id counters for entities.

        Raises:
            DatabaseError: If any sequence reset operation fails.
        """
        execute_write_tx(cursor, QUERIES.world_state.reset_customer_sequence, (counters.next_customer_id,))
        execute_write_tx(cursor, QUERIES.world_state.reset_route_sequence, (counters.next_route_id,))
        execute_write_tx(cursor, QUERIES.world_state.reset_package_sequence, (counters.next_package_id,))
