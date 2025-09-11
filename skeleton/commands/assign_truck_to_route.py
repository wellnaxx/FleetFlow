from commands.base_command.base_command import BaseCommand
from core.application_data import ApplicationData
from commands.validation_helpers import try_parse_int
from commands.find_suitable_trucks_for_route import FindSuitableTrucksForRoute

class AssignTruckToRoute(BaseCommand):
    def __init__(self, params: list[str], app_data: ApplicationData):
        super().__init__(params, app_data)
        self._params = params
        self._app_data = app_data

    def execute(self):
        route_id = try_parse_int(self._params[0])
        truck_id = try_parse_int(self._params[1])

        find_command = FindSuitableTrucksForRoute([route_id], self._app_data)
        find_command.execute()
        suitable_trucks = find_command.raw_trucks

        if truck_id not in [truck.vehicle_id for truck in suitable_trucks]:
            raise ValueError(f"Truck {truck_id} cannot be assigned to route {route_id}")
        
        route = self._app_data.find_route(route_id)
        self._app_data.vehicle_manager.assign_truck_to_route(truck_id, route, route.calculate_km)
        return f"Truck {truck_id} was assigned successfully to route {route_id}"
        