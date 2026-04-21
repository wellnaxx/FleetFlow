from src.adapters.driving.cli.commands.base_command.base_command import UseCaseCommand
from src.adapters.driving.cli.commands.validation_helpers import try_parse_int, validate_params_exact
from src.application.services.authorization import requires_all
from src.application.use_cases.routes.find_suitable_routes_for_package import (
    FindSuitableRoutesForPackageUseCase,
)
from src.domain.enums.auth import Permission


class FindSuitableRoutesForPackage(UseCaseCommand[FindSuitableRoutesForPackageUseCase]):
    """Find candidate routes for the package's origin→destination.

    Returns:
        List of dicts with:
            - 'route': DeliveryRoute
            - 'eta': datetime or None
            - 'capacity_left': float (kg) or None when no truck
    """

    @requires_all(Permission.PACKAGE_FIND_ROUTE_FOR, Permission.PACKAGE_VIEW, Permission.ROUTE_VIEW)
    def execute(self) -> str:
        validate_params_exact(self._params, 1)
        package_id = try_parse_int(self._params[0])
        
        matches = self._use_case.execute(package_id)
        if not matches:
            return "No suitable routes found."

        lines: list[str] = []
        for match in matches:
            route = match.route
            eta_str = match.eta.strftime("%Y-%m-%d %H:%M") if match.eta else "N/A"
            cap_str = f"{match.capacity_left:.2f}kg" if match.capacity_left is not None else "No truck"

            lines.append(
                f"Route {route.route_id}: {route.start_location} → {route.end_location}, "
                f"ETA to {match.end_city}: {eta_str}, "
                f"Capacity left: {cap_str}"
            )

        return "\n".join(lines)
