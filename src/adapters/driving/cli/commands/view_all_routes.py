"""CLI command for listing routes."""

from src.adapters.driving.cli.commands.base_command.base_command import BaseCommand
from src.application.services.authorization_service import requires
from src.application.use_cases.routes.view_all_routes import ViewAllRoutesUseCase
from src.domain.enums.auth import Permission


class ViewAllRoutes(BaseCommand[ViewAllRoutesUseCase]):
    """Render all routes."""

    @requires(Permission.ROUTE_VIEW_ALL)
    def execute(self) -> str:
        """Return route listing text.

        Returns:
            CLI listing of routes, or an empty-state message.

        Raises:
            PermissionError: If the caller lacks route listing permission.
        """
        routes = self._use_case.execute()
        return "\n\n".join(r.info() for r in routes) if routes else "No routes available."

