"""Transaction-bound truck repository for Postgres unit-of-work operations."""

from psycopg import Cursor

from src.adapters.driven.persistence.database.executor import execute_write_tx
from src.adapters.driven.persistence.database.queries import QUERIES
from src.domain.entities.truck import Truck


class PostgresTruckUnitOfWorkRepository:
    """Persist truck state using a shared transaction cursor."""

    def __init__(self, cursor: Cursor) -> None:
        """Initialize the repository with a transaction cursor.

        Args:
            cursor: Cursor owned by the active unit of work.
        """
        self._cursor = cursor

    def update_state(self, truck: Truck) -> None:
        """Persist mutable truck runtime state.

        Args:
            truck: Truck whose current runtime state should be persisted.

        Returns:
            None.

        Raises:
            DatabaseError: If the update operation fails.
            ValueError: If the truck row no longer exists.
        """
        affected = execute_write_tx(
            self._cursor,
            QUERIES.trucks.update_state,
            (
                truck.status.value,
                str(truck.current_location) if truck.current_location is not None else None,
                truck.busy_from,
                truck.busy_until,
                str(truck.in_transit_to) if truck.in_transit_to is not None else None,
                truck.vehicle_id,
            ),
        )
        if affected != 1:
            raise ValueError(
                f"Expected to update one truck row for id {truck.vehicle_id}, affected {affected}."
            )
