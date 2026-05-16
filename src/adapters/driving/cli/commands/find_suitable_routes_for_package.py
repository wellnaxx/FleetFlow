"""CLI command for finding suitable routes for a package."""

from src.adapters.driving.cli.commands.base_command.base_command import BaseCommand
from src.adapters.driving.cli.commands.validation_helpers import try_parse_int, validate_params_exact
from src.application.use_cases.routes.find_suitable_routes_for_package import (
    FindSuitableRoutesForPackageUseCase,
)


class FindSuitableRoutesForPackage(BaseCommand[FindSuitableRoutesForPackageUseCase]):
    """Find candidate routes for the package's origin-to-destination."""

    def execute(self) -> str:
        """List route candidates for a package.

        Returns:
            CLI table-like summary, or a no-match message.

        Raises:
            PermissionError: If the caller lacks required view/search permissions.
            ValueError: If the package id is invalid or missing.
        """
        validate_params_exact(self._params, 1)
        package_id = try_parse_int(self._params[0])

        matches = self._use_case.execute(package_id)
        if not matches:
            return "No suitable routes found."

        lines: list[str] = []
        for match in matches:
            eta_str = match.eta.strftime("%Y-%m-%d %H:%M") if match.eta else "N/A"
            cap_str = f"{match.capacity_left:.2f}kg" if match.capacity_left is not None else "No truck"
            lines.append(
                f"Route {match.route_id}: {match.start_location} -> {match.end_location}, "
                f"ETA to {match.end_city}: {eta_str}, "
                f"Capacity left: {cap_str}"
            )

        return "\n".join(lines)
