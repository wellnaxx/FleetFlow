from src.adapters.driven.persistence.database.executor import (
    execute_write,
    fetch_all,
    fetch_one,
)
from src.adapters.driven.persistence.database.mappers import map_truck
from src.adapters.driven.persistence.database.queries import QUERIES
from src.domain.entities.truck import Truck


class PostgresTruckRepository:
    """Postgres-backed truck repository implementation."""

    def add(self, truck: Truck) -> None:
        """Persist a fleet truck.

        Args:
            truck: Truck to add to the fleet.

        Returns:
            None.

        Raises:
            DatabaseError: If the insert operation fails.
        """
        execute_write(
            QUERIES.trucks.add,
            (
                truck.vehicle_id,
                truck.name.value,
                truck.capacity,
                truck.max_range,
                truck.status.value,
                str(truck.current_location) if truck.current_location is not None else None,
                truck.busy_from,
                truck.busy_until,
                str(truck.in_transit_to) if truck.in_transit_to is not None else None,
            ),
        )

    def list_fleet(self) -> list[Truck]:
        """Return all persisted fleet trucks.

        Returns:
            Fleet trucks ordered by vehicle id.

        Raises:
            DatabaseError: If the select operation fails.
            KeyError: If a required truck column is missing.
            TypeError: If a required truck column has an unexpected type.
            ValueError: If persisted truck data is invalid.
        """
        truck_rows = fetch_all(QUERIES.trucks.list_all)
        return [map_truck(truck_row) for truck_row in truck_rows]

    def find_by_id(self, vehicle_id: int) -> Truck | None:
        """Return a truck by vehicle id.

        Args:
            vehicle_id: Fleet vehicle id to look up.

        Returns:
            Matching truck, or `None` when absent.

        Raises:
            DatabaseError: If the select operation fails.
            KeyError: If a required truck column is missing.
            TypeError: If a required truck column has an unexpected type.
            ValueError: If persisted truck data is invalid.
        """
        truck_row = fetch_one(QUERIES.trucks.get_by_id, (vehicle_id,))
        if truck_row is None:
            return None

        return map_truck(truck_row)

    def update_state(self, truck: Truck) -> None:
        """Persist mutable truck runtime state.

        Args:
            truck: Truck whose current runtime state should be persisted.

        Returns:
            None.

        Raises:
            DatabaseError: If the update operation fails.
        """
        execute_write(
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
