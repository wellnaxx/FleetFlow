"""Use case for listing fleet trucks."""

from src.domain.entities.truck import Truck
from src.ports.output.vehicle_manager import VehicleManagerPort


class ViewAllTrucksUseCase:
    """List all trucks managed by the vehicle manager."""

    def __init__(self, vehicles: VehicleManagerPort) -> None:
        """Initialize the use case.

        Args:
            vehicles: Vehicle manager used to list fleet state.
        """
        self._vehicles = vehicles

    def execute(self) -> list[Truck]:
        """Return the current fleet listing.

        Returns:
            Trucks currently known to the vehicle manager.
        """
        return self._vehicles.list_fleet()
