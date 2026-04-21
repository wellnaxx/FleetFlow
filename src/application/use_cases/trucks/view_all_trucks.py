from src.domain.entities.truck import Truck
from src.ports.output.vehicle_manager import VehicleManagerPort


class ViewAllTrucksUseCase:
    def __init__(self, vehicles: VehicleManagerPort) -> None:
        self._vehicles = vehicles

    def execute(self) -> list[Truck]:
        return self._vehicles.list_fleet()
