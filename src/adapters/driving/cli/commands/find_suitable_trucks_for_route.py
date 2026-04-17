from src.adapters.driving.cli.commands.base_command.base_command import BaseCommand
from src.adapters.driving.cli.commands.validation_helpers import try_parse_int, validate_params_exact


class FindSuitableTrucksForRoute(BaseCommand):
    def execute(self) -> str:
        validate_params_exact(self._params, 1)
        route_id = try_parse_int(self._params[0])
        if not self._app_data.find_route(route_id):
            raise ValueError(f"Route with ID {route_id} not found")
        trucks = self._app_data.find_suitable_trucks_for_route(route_id)
        if not trucks:
            return "No suitable trucks found."
        lines = ["ID | Name   | Capacity | Max Range | Current Location"]
        lines.extend(
            f"{t.vehicle_id} | {t.name} | {t.capacity} kg | {t.max_range} km | {t.current_location}"
            for t in trucks
        )
        return "\n".join(lines)

    @property
    def raw_trucks(self) -> list[object]:
        return getattr(self, "_raw_suitable_trucks", [])
