from src.adapters.driving.cli.commands.base_command.base_command import BaseCommand
from src.adapters.driving.cli.commands.validation_helpers import try_parse_int, validate_params_exact


class ViewRoute(BaseCommand):
    def execute(self) -> str:
        validate_params_exact(self._params, 1)
        route_id = try_parse_int(self._params[0])
        route = self._app_data.view_route(route_id)
        if not route:
            raise ValueError(f"Route with ID {route_id} not found")
        return route.info()
