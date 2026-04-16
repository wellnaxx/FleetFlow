from adapters.driving.cli.commands.base_command.base_command import BaseCommand
from adapters.driving.cli.commands.validation_helpers import try_parse_int, validate_params_exact


class FindSuitableRoutesForPackage(BaseCommand):
    """Find candidate routes for the package's origin→destination.

    Returns:
        List of dicts with:
            - 'route': DeliveryRoute
            - 'eta': datetime or None
            - 'capacity_left': float (kg) or None when no truck
    """

    def execute(self) -> str:
        validate_params_exact(self._params, 1)
        package_id = try_parse_int(self._params[0])
        pkg = self._app_data.view_package(package_id)
        if not pkg:
            raise ValueError(f"Package with ID {package_id} not found")
        end_city = pkg.end_location

        matches = self._app_data.find_suitable_routes_for_package(package_id)
        if not matches:
            return "No suitable routes found."

        lines: list[str] = []
        for m in matches:
            r = m["route"]
            eta = m["eta"]
            eta_str = eta.strftime("%Y-%m-%d %H:%M") if eta else "N/A"
            if r.truck:
                cap_left = m["capacity_left"]
                cap_str = f"{cap_left:.2f}kg"
            else:
                cap_str = "No truck"
            lines.append(
                f"Route {r.route_id}: {r.start_location} → {r.end_location}, "
                f"ETA to {end_city}: {eta_str}, "
                f"Capacity left: {cap_str}"
            )
        return "\n".join(lines)
