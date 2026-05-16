"""Use case for listing all routes."""

from src.application.services.authorization_service import AuthorizationService, requires
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.enums.auth import Permission
from src.ports.output.route_repository import RouteRepositoryPort


class ViewAllRoutesUseCase(AuthorizedUseCase[list[DeliveryRoute]]):
    """List all routes from the repository."""

    def __init__(self, routes: RouteRepositoryPort, authz: AuthorizationService) -> None:
        """Initialize the use case.

        Args:
            routes: Repository used to list routes.
            authz: Service used for authorization checks.
        """
        super().__init__(authz)
        self._routes = routes

    @requires(Permission.ROUTE_VIEW_ALL)
    def execute(self) -> list[DeliveryRoute]:
        """Return all persisted routes.

        Returns:
            Route entities currently stored in the repository.
        """
        return self._routes.list_all()
