from commands.base_command.base_command import  BaseCommand
from core.application_data import ApplicationData
from commands.validation_helpers import validate_params_count, try_parse_float
from core.map import Map

class CreatePackage(BaseCommand):
    def __init__(self, params: list[str], app_data: ApplicationData):
        super().__init__(params, app_data)
        validate_params_count(params, 4, 6)
        self._params = params
        self._app_data = app_data

    def execute(self):
        if not Map.is_valid_location(self._params[0]):
            raise ValueError(f"Invalid start location: {self._params[0]}")
        start_location = self._params[0]
        if not Map.is_valid_location(self._params[1]):
            raise ValueError(f"Invalid end location: {self._params[1]}")
        end_location = self._params[1]
        weight = try_parse_float(self._params[2])
        name = self._params[3]

        email = self._params[4].strip() if len(self._params) > 4 else None
        phone = self._params[5].strip() if len(self._params) > 5 else None

        self._app_data.create_package(start_location, end_location, weight, name, email, phone)
        return f"Package was created for customer {name} successfully."

