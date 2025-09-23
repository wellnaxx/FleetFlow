from src.commands.base_command.base_command import BaseCommand
from src.commands.validation_helpers import try_parse_int, validate_params_exact

class RemoveRoute(BaseCommand):
    mutates_state = True
    def execute(self):
        validate_params_exact(self._params, 1)
        route_id = try_parse_int(self._params[0])
        self._app_data.remove_route(route_id)
        return f"Route {route_id} removed."
