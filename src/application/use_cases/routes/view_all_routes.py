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
    def execute(self, limit: int | None = None, offset: int = 0) -> list[DeliveryRoute]:
        """Return all persisted routes.

        Args:
            limit: Optional maximum number of routes to return.
            offset: Number of routes to skip when `limit` is provided.

        Returns:
            Route entities currently stored in the repository.

        Raises:
            ValueError: If pagination arguments are invalid.
        """
        if limit is None:
            if offset != 0:
                raise ValueError("Offset cannot be used without a limit.")
            return self._routes.list_all()

        if limit < 1:
            raise ValueError("Limit must be greater than zero.")
        if offset < 0:
            raise ValueError("Offset must be greater than or equal to zero.")

        return self._routes.list_page(limit=limit, offset=offset)

    @requires(Permission.ROUTE_VIEW_ALL)
    def execute_with_count(self, limit: int, offset: int = 0) -> tuple[list[DeliveryRoute], int]:
        """Return a route page and total from one repository operation."""
        if limit < 1:
            raise ValueError("Limit must be greater than zero.")
        if offset < 0:
            raise ValueError("Offset must be greater than or equal to zero.")

        return self._routes.list_page_with_total(limit=limit, offset=offset)

    @requires(Permission.ROUTE_VIEW_ALL)
    def count(self) -> int:
        """Return the total number of persisted routes."""
        return self._routes.count_all()
