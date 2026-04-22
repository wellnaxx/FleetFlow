from src.adapters.driving.cli.commands.base_command.base_command import BaseCommand
from src.adapters.driving.cli.commands.validation_helpers import try_parse_int, validate_params_exact
from src.application.services.authorization_service import requires_all
from src.application.use_cases.routes.remove_route import RemoveRouteUseCase
from src.domain.enums.auth import Permission


class RemoveRoute(BaseCommand[RemoveRouteUseCase]):
    mutates_state = True
    autosaves_state = True

    @requires_all(Permission.ROUTE_REMOVE, Permission.ROUTE_VIEW)
    def execute(self) -> str:
        validate_params_exact(self._params, 1)
        route_id = try_parse_int(self._params[0])
        self._use_case.execute(route_id)
        return f"Route {route_id} removed."
