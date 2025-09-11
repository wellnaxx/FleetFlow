from commands.base_command.base_command import BaseCommand
from core.application_data import ApplicationData

class FindSuitableTrucksForRoute(BaseCommand):
    def __init__(self, params: list[str], app_data: ApplicationData):
        super().__init__(params, app_data)
        self._params = params
        self._app_data = app_data

    def execute(self):
        route = self.app_data.find_route(self._params[0])
        suitable_trucks = self.app_data.vehicle_manager.find_available_trucks(route, route.calculate_km, route.departure_time, route.arrival_time)
        self._raw_suitable_trucks = suitable_trucks
        
        if not suitable_trucks:
            return "No suitable trucks available for this route"
        
        formatted = ["ID | Name   | Capacity | Max Range | Current Location"]
        
        for truck in suitable_trucks:
            formatted.append(f"{truck.vehicle_id} | {truck.name} | {truck.capacity} kg | {truck.max_range} km | {truck.current_location}")
        return "\n".join(formatted)
    
    @property
    def raw_trucks(self):
        return getattr(self, "_raw_suitable_trucks", [])
