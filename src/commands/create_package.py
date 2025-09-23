from src.commands.base_command.base_command import BaseCommand
from src.commands.validation_helpers import validate_params_count, try_parse_float
from src.models.map import Map

class CreatePackage(BaseCommand):
    mutates_state = True
    def execute(self):
        validate_params_count(self._params, 4, 6)
        if not Map.is_valid_location(self._params[0]):
            raise ValueError(f"Invalid start location: {self._params[0]}")
        if not Map.is_valid_location(self._params[1]):
            raise ValueError(f"Invalid end location: {self._params[1]}")
        start, end = self._params[0], self._params[1]
        weight = try_parse_float(self._params[2])
        name = self._params[3]
        email = self._params[4] if len(self._params)>4 else ""
        phone = self._params[5] if len(self._params)>5 else ""
        pkg = self._app_data.create_package(start, end, weight, name, email, phone)
        return f"Package {pkg.package_id} was created for customer {name} (ID: {pkg.customer.customer_id}) successfully."
