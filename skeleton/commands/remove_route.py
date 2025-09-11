from commands.base_command.base_command import BaseCommand
from core.application_data import ApplicationData
from commands.validation_helpers import try_parse_int

class RemoveRoute(BaseCommand):
    def __init__(self, params: list[str], app_data: ApplicationData):
        super().__init__(params, app_data)
        self._params = params
        self._app_data = app_data

    def execute(self):
        route_id = try_parse_int(self._params[0])
        route = self.app_data.find_route(route_id)

        if not route:
            return f"Route with ID {route_id} not found!"
        self.app_data.remove_route(route)
        return f"Route with ID {route_id} was removed!"