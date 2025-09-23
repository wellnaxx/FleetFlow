from src.commands.base_command.base_command import BaseCommand
from src.commands.validation_helpers import try_parse_int, validate_params_count

class AssignPackageToRoute(BaseCommand):
    """Attach a package to a route subject to capacity/range constraints.

        Args:
            route_id: Target route id.
            package_id: Package to assign.
        Raises:
            ValueError: If not found or constraints fail.
        """
    mutates_state = True
    def execute(self):
        validate_params_count(self._params, 2)
        route_id = try_parse_int(self._params[0])
        package_ids = [try_parse_int(pid) for pid in self._params[1:]]
        messages = self._app_data.assign_packages_to_route(route_id, package_ids)
        return "\n".join(messages)
