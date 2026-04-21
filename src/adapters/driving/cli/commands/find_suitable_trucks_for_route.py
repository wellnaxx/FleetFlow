from src.adapters.driving.cli.commands.base_command.base_command import UseCaseCommand
from src.adapters.driving.cli.commands.validation_helpers import try_parse_int, validate_params_exact
from src.application.services.authorization import requires
from src.application.use_cases.routes.find_suitable_trucks_for_route import FindSuitableTrucksForRouteUseCase
from src.domain.enums.auth import Permission


class FindSuitableTrucksForRoute(UseCaseCommand[FindSuitableTrucksForRouteUseCase]):
    @requires(Permission.ROUTE_FIND_TRUCK_FOR)
    def execute(self) -> str:
        validate_params_exact(self._params, 1)
        route_id = try_parse_int(self._params[0])
        trucks = self._use_case.execute(route_id)
        if not trucks:
            return "No suitable trucks found."
        lines = ["ID | Name   | Capacity | Max Range | Current Location"]
        lines.extend(
            f"{t.vehicle_id} | {t.name} | {t.capacity} kg | {t.max_range} km | {t.current_location}"
            for t in trucks
        )
        return "\n".join(lines)
