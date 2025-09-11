from commands.base_command.base_command import BaseCommand
from core.application_data import ApplicationData

class FindRoute(BaseCommand):
    def __init__(self, params: list[str], app_data: ApplicationData):
        super().__init__(params, app_data)
        self._params = params
        self._app_data = app_data

    def execute(self):
        route_id = int(self._params[0])
        route = self.app_data.find_route(route_id)

        if not route:
            return f"Route with ID {route_id} not found!"
        return f"Route with ID {route.route_id} was found!"
