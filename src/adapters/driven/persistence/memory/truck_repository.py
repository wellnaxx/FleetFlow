from src.composition.seed_fleet import build_default_fleet
from src.domain.entities.truck import Truck


class InMemoryTruckRepository:
    def __init__(self) -> None:
        """Create the default fixed fleet and disperse trucks across locations."""
        self.vehicles: list[Truck] = build_default_fleet()

    def add(self, truck: Truck) -> None:
        """Add a truck to the in-memory fleet.

        Args:
            truck: Truck to add to the fleet.

        Returns:
            None.
        """
        self.vehicles.append(truck)

    def list_fleet(self) -> list[Truck]:
        """Return a copy of the repository's fleet list.

        Returns:
            Trucks currently stored by the repository.
        """
        return list(self.vehicles)

    def find_by_id(self, vehicle_id: int) -> Truck | None:
        """Return a truck by vehicle id, if it exists.

        Args:
            vehicle_id: Truck identifier to look up.

        Returns:
            Matching truck, or None when no truck exists.
        """
        for v in self.vehicles:
            if v.vehicle_id == vehicle_id:
                return v
        return None

    def update_state(self, truck: Truck) -> None:
        """Persist mutable truck runtime state. For in-memory truck repository, it is a no-op.

        Args:
            truck: Truck whose current runtime state should be persisted.

        Returns:
            None.
        """
