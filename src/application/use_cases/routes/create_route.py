"""Use case for creating a delivery route."""

import logging
from collections.abc import Sequence
from datetime import datetime

from src.application.services.authorization_service import AuthorizationService, requires
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.enums.auth import Permission
from src.ports.output.route_repository import RouteRepositoryPort

logger = logging.getLogger(__name__)


class CreateRouteUseCase(AuthorizedUseCase[DeliveryRoute]):
    """Create and persist delivery routes."""

    def __init__(self, routes: RouteRepositoryPort, authz: AuthorizationService) -> None:
        """Initialize the use case.

        Args:
            routes: Repository used to allocate and persist routes.
            authz: Service used for authorization checks.
        """
        super().__init__(authz)
        self._routes = routes

    @requires(Permission.ROUTE_CREATE)
    def execute(self, locations: Sequence[str], departure_time: datetime | None) -> DeliveryRoute:
        """Create and persist a delivery route.

        Args:
            locations: Ordered list of raw or typed route stops.
            departure_time: Optional initial departure time.

        Returns:
            The newly created route.

        Raises:
            PermissionError: If the caller lacks route creation permission.
            DatabaseError: If the route creation persistence fails.
            DomainValidationError: If the route has too few stops or contains invalid locations.
        """

        route = self._routes.create(locations=locations, departure_time=departure_time)
        logger.info(
            "Created route %d from %s to %s with %d stops.",
            route.route_id,
            route.start_location,
            route.end_location,
            len(route.locations),
        )
        return route
