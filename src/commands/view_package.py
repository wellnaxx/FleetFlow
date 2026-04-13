from src.commands.base_command.base_command import BaseCommand
from src.commands.validation_helpers import try_parse_int, validate_params_exact


class ViewPackage(BaseCommand):
    def execute(self) -> str:
        validate_params_exact(self._params, 1)
        package_id = try_parse_int(self._params[0])
        p = self._app_data.view_package(package_id)
        if not p:
            raise ValueError(f"Package with ID {package_id} not found")
        return p.info()
