from commands.base_command.base_command import BaseCommand
from core.application_data import ApplicationData
from commands.validation_helpers import try_parse_int


class ViewPackage(BaseCommand):
    def __init__(self, params: list[str], app_data: ApplicationData):
        super().__init__(params, app_data)
        self._params = params
        self._app_data = app_data


    def execute(self):
        package_id = try_parse_int(self._params[0])
        package = self._app_data.view_package(package_id)

        if not package:
            raise ValueError(f"Package with ID {package_id} not found")
        
        return package.info()