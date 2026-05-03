from typing import Protocol

from src.domain.entities.truck import Truck


class TruckRepositoryPort(Protocol):
    """Persist and query fleet truck state."""

    def add(self, truck: Truck) -> None:
        """Persist a fleet truck.

        Args:
            truck: Truck to add to the fleet.

        Returns:
            None.
        """
        ...

    def list_fleet(self) -> list[Truck]:
        """Return all persisted fleet trucks.

        Returns:
            Fleet trucks ordered by repository implementation.
        """
        ...

    def find_by_id(self, vehicle_id: int) -> Truck | None:
        """Return a truck by vehicle id.

        Args:
            vehicle_id: Fleet vehicle id to look up.

        Returns:
            Matching truck, or `None` when absent.
        """
        ...

    def update_state(self, truck: Truck) -> None:
        """Persist mutable truck runtime state.

        Args:
            truck: Truck whose current runtime state should be persisted.

        Returns:
            None.
        """
        ...
