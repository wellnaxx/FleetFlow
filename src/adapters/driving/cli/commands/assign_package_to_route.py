"""CLI command for assigning packages to routes."""

from src.adapters.driving.cli.commands.base_command.base_command import BaseCommand
from src.adapters.driving.cli.commands.validation_helpers import try_parse_int, validate_params_count
from src.application.services.authorization_service import requires
from src.application.use_cases.routes.assign_packages_to_route import AssignPackagesToRouteUseCase
from src.domain.enums.auth import Permission


class AssignPackageToRoute(BaseCommand[AssignPackagesToRouteUseCase]):
    """Attach one or more packages to a route."""

    mutates_state = True
    autosaves_state = True

    @requires(Permission.ROUTE_ASSIGN_PACKAGE)
    def execute(self) -> str:
        """Assign one or more packages to a route.

        Returns:
            CLI summary of successful assignments and per-package failures.

        Raises:
            PermissionError: If the caller lacks package-assignment permission.
            ValueError: If route id or package ids are invalid CLI values.
        """
        validate_params_count(self._params, 2)

        route_id = try_parse_int(self._params[0])
        package_ids = [try_parse_int(pid) for pid in self._params[1:]]

        result = self._use_case.execute(route_id, package_ids)

        success_lines = [
            f"Assigned package {s.package_id} to route {s.route_id}. ETA: {s.eta_text}"
            for s in result.successes
        ]

        error_lines = [e.message for e in result.errors]

        parts: list[str] = []
        if success_lines:
            parts.append("\n".join(success_lines))
        if error_lines:
            parts.append("Failed:\n- " + "\n- ".join(error_lines))

        return "\n\n".join(parts)
