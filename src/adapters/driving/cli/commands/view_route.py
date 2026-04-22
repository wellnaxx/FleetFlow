from src.adapters.driving.cli.commands.base_command.base_command import BaseCommand
from src.adapters.driving.cli.commands.validation_helpers import try_parse_int, validate_params_exact
from src.application.services.authorization_service import requires
from src.application.use_cases.routes.view_route import ViewRouteUseCase
from src.domain.enums.auth import Permission


class ViewRoute(BaseCommand[ViewRouteUseCase]):
    @requires(Permission.ROUTE_VIEW)
    def execute(self) -> str:
        validate_params_exact(self._params, 1)
        route_id = try_parse_int(self._params[0])
        route = self._use_case.execute(route_id)
        return route.info()

