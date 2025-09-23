from src.commands.base_command.base_command import BaseCommand
from src.commands.validation_helpers import try_parse_int, validate_params_exact

class RemovePackage(BaseCommand):
    """
    Remove a delivery package by ID.

    Usage:
      removepackage <package_id>
      removepackage <package_id> 

    Examples:
      removepackage 42
      removepackage 42
    """


    mutates_state = True

    def execute(self):
        validate_params_exact(self._params, 1)
        package_id = try_parse_int(self._params[0])
        self._app_data.remove_package(package_id)
        return f"Package {package_id} removed."