from src.domain.entities.truck import Truck
from src.ports.output.vehicle_manager import VehicleManagerPort


class ViewAllTrucksUseCase:
    """List all trucks managed by the vehicle manager."""

    def __init__(self, vehicles: VehicleManagerPort) -> None:
        self._vehicles = vehicles

    def execute(self) -> list[Truck]:
        """Return the current fleet listing."""
        return self._vehicles.list_fleet()
