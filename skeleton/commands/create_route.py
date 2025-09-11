from commands.base_command.base_command import  BaseCommand
from core.application_data import ApplicationData
from datetime import datetime

class CreateRoute(BaseCommand):
    def __init__(self, params: list[str], app_data: ApplicationData):
        super().__init__(params, app_data)
        self._params = params
        self._app_data = app_data

    def execute(self):
        locations = [location.strip().upper().rstrip(",") for location in self._params[0].split(",")]
        route = self.app_data.create_route(locations)

        return f"Route with ID {route.route_id} was created!"

