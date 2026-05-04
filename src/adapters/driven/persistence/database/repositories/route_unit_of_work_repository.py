"""Transaction-bound route repository for Postgres unit-of-work operations."""

from psycopg import Cursor

from src.adapters.driven.persistence.database.executor import execute_write_tx
from src.adapters.driven.persistence.database.queries import QUERIES
from src.domain.entities.delivery_route import DeliveryRoute


class PostgresRouteUnitOfWorkRepository:
    """Persist route state using a shared transaction cursor."""

    def __init__(self, cursor: Cursor) -> None:
        """Initialize the repository with a transaction cursor.

        Args:
            cursor: Cursor owned by the active unit of work.
        """
        self._cursor = cursor

    def update_state(self, route: DeliveryRoute) -> None:
        """Persist mutable route runtime state.

        Args:
            route: Route whose current runtime state should be persisted.

        Returns:
            None.

        Raises:
            DatabaseError: If the update operation fails.
            ValueError: If the route row no longer exists.
        """
        truck_vehicle_id = route.truck.vehicle_id if route.truck is not None else None
        affected = execute_write_tx(
            self._cursor,
            QUERIES.routes.update_state,
            (
                route.departure_time,
                route.status.value,
                truck_vehicle_id,
                route.route_id,
            ),
        )
        if affected != 1:
            raise ValueError(f"Expected to update one route row for id {route.route_id}, affected {affected}.")

    def remove(self, route_id: int) -> None:
        """Remove a route by id inside the active transaction.

        Args:
            route_id: Route id to remove.

        Returns:
            None.

        Raises:
            DatabaseError: If the delete operation fails.
            ValueError: If the route row no longer exists.
        """
        affected = execute_write_tx(self._cursor, QUERIES.routes.remove, (route_id,))
        if affected != 1:
            raise ValueError(f"Expected to remove one route row for id {route_id}, affected {affected}.")
