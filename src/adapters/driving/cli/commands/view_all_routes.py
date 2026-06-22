"""CLI command for listing routes."""

from src.adapters.driving.cli.commands.base_command.base_command import BaseCommand
from src.adapters.driving.cli.rendering.route_info_renderer import render_route_info
from src.application.use_cases.routes.view_all_routes import ViewAllRoutesUseCase


class ViewAllRoutes(BaseCommand[ViewAllRoutesUseCase]):
    """Render all routes."""

    def execute(self) -> str:
        """Return route listing text.

        Returns:
            CLI listing of routes, or an empty-state message.

        Raises:
            PermissionError: If the caller lacks route listing permission.
        """
        routes = self._use_case.execute().items
        return "\n\n".join(render_route_info(route) for route in routes) if routes else "No routes available."
