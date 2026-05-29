"""Use case for listing routes currently in progress."""

from datetime import datetime

from src.application.services.authorization_service import AuthorizationService, requires
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.domain.entities.delivery_route import DeliveryRoute, RoutePosition
from src.domain.enums.auth import Permission
from src.ports.output.route_repository import RouteRepositoryPort


class ViewRoutesInProgressUseCase(AuthorizedUseCase[list[tuple[DeliveryRoute, RoutePosition]]]):
    """List routes that are currently active at the supplied time."""

    def __init__(self, routes: RouteRepositoryPort, authz: AuthorizationService) -> None:
        """Initialize the use case.

        Args:
            routes: Repository used to list routes.
            authz: Service used for authorization checks.
        """
        super().__init__(authz)
        self._routes = routes

    @requires(Permission.ROUTE_VIEW_IN_PROGRESS)
    def execute(self, now: datetime) -> list[tuple[DeliveryRoute, RoutePosition]]:
        """Return routes currently at a stop or in transit.

        Args:
            now: Clock value used to compute each route's position.

        Returns:
            A list of `(route, position)` tuples for active routes.

        Raises:
            PermissionError: If the caller lacks in-progress routes view permission.
            DatabaseError: If the in-progress routes view persistence fails.
        """
        active: list[tuple[DeliveryRoute, RoutePosition]] = []

        for route in self._routes.list_all():
            pos = route.current_position(now)
            if pos.kind in {"AT_STOP", "IN_TRANSIT"}:
                active.append((route, pos))

        return active
