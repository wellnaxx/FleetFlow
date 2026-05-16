"""CLI command for viewing a route."""

from src.adapters.driving.cli.commands.base_command.base_command import BaseCommand
from src.adapters.driving.cli.commands.validation_helpers import try_parse_int, validate_params_exact
from src.application.use_cases.routes.view_route import ViewRouteUseCase


class ViewRoute(BaseCommand[ViewRouteUseCase]):
    """Render one route by id."""

    def execute(self) -> str:
        """Fetch a route and return display text.

        Returns:
            Multi-line route summary.

        Raises:
            PermissionError: If the caller lacks route view permission.
            ValueError: If the parameter count or route id is invalid.
        """
        validate_params_exact(self._params, 1)
        route_id = try_parse_int(self._params[0])
        route = self._use_case.execute(route_id)
        return route.info()
