from src.adapters.driving.cli.commands.base_command.base_command import UseCaseCommand
from src.application.services.authorization_service import requires
from src.application.use_cases.routes.view_all_routes import ViewAllRoutesUseCase
from src.domain.enums.auth import Permission


class ViewAllRoutes(UseCaseCommand[ViewAllRoutesUseCase]):
    @requires(Permission.ROUTE_VIEW_ALL)
    def execute(self) -> str:
        routes = self._use_case.execute()
        return "\n\n".join(r.info() for r in routes) if routes else "No routes available."
