"""CLI command for removing delivery routes."""

from src.adapters.driving.cli.commands.base_command.event_draining_command import EventDrainingCommand
from src.adapters.driving.cli.commands.validation_helpers import try_parse_int, validate_params_exact
from src.application.use_cases.routes.remove_route import RemoveRouteUseCase


class RemoveRoute(EventDrainingCommand[RemoveRouteUseCase]):
    """Remove a route by id."""

    mutates_state = True
    autosaves_state = True

    def execute(self) -> str:
        """Remove the requested route.

        Returns:
            CLI confirmation text.

        Raises:
            PermissionError: If the caller lacks required route permissions.
            ValueError: If the route id is invalid or the route is missing.
        """
        validate_params_exact(self._params, 1)
        route_id = try_parse_int(self._params[0], "route_id")
        route = self._run_and_drain(
            self._use_case,
            lambda: self._use_case.execute(route_id),
        )

        self._event_collector.drain((route,))
        return f"Route {route_id} removed."
