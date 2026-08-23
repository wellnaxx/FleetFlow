"""Command-bus-backed CLI command for assigning packages to routes."""

from src.adapters.driving.cli.commands.base_command.command_bus_command import CommandBusCommand
from src.adapters.driving.cli.commands.validation_helpers import try_parse_int, validate_params_count
from src.application.commands.routes.assign_packages_to_route import (
    ASSIGN_PACKAGES_TO_ROUTE,
    AssignPackagesToRouteCommand,
)


class AssignPackagesToRoute(CommandBusCommand):
    """Attach one or more packages to a route."""

    mutates_state = True
    autosaves_state = True

    def execute(self) -> str:
        """Assign one or more packages to a route.

        Returns:
            CLI summary of successful assignments and per-package failures.

        Raises:
            PermissionError: If the caller lacks package-assignment permission.
            ValueError: If route id or package ids are invalid CLI values.
            NotFoundError: If the target route does not exist.
            DatabaseError: If assignment persistence or event publication
                fails.
        """
        validate_params_count(self._params, 2)

        route_id = try_parse_int(self._params[0], "route_id")
        package_ids = [try_parse_int(pid, "package_id") for pid in self._params[1:]]

        result = self.command_bus.dispatch(
            key=ASSIGN_PACKAGES_TO_ROUTE,
            command=AssignPackagesToRouteCommand(
                route_id=route_id,
                package_ids=tuple(package_ids),
            ),
        )

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
