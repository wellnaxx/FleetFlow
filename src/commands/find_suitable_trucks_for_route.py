from src.commands.base_command.base_command import BaseCommand
from src.commands.validation_helpers import try_parse_int, validate_params_exact

class FindSuitableTrucksForRoute(BaseCommand):
    def execute(self):
        validate_params_exact(self._params, 1)
        route_id = try_parse_int(self._params[0])
        if not self._app_data.find_route(route_id):
            raise ValueError(f"Route with ID {route_id} not found")
        trucks = self._app_data.find_suitable_trucks_for_route(route_id)
        if not trucks:
            return "No suitable trucks found."
        lines = ["ID | Name   | Capacity | Max Range | Current Location"]
        for t in trucks:
            lines.append(f"{t.vehicle_id} | {t.name} | {t.capacity} kg | {t.max_range} km | {t.current_location}")
        return "\n".join(lines)

    @property
    def raw_trucks(self):
        return getattr(self, "_raw_suitable_trucks", [])
