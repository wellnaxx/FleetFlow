from commands.base_command.base_command import BaseCommand
from core.application_data import ApplicationData

class ViewRoute(BaseCommand):
    def __init__(self, params: list[str], app_data: ApplicationData):
        super().__init__(params, app_data)
        self._params = params
        self._app_data = app_data

    def execute(self):
        routes = self.app_data.view_routes()

        if not routes:
            return "No routes available."
        return " \n\n".join(routes)