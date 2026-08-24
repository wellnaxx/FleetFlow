"""Use case for creating a delivery route."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.authorization_operations import AuthorizationOperation
from src.application.services.authorization_service import AuthorizationService, requires
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.enums.auth import Permission

if TYPE_CHECKING:
    from src.application.commands.routes.create_route import CreateRouteCommand
    from src.ports.output.route_repository import RouteRepositoryPort

logger = logging.getLogger(__name__)


class CreateRouteUseCase(AuthorizedUseCase[DeliveryRoute]):
    """Create routes through the published application command contract."""

    def __init__(self, routes: RouteRepositoryPort, authz: AuthorizationService) -> None:
        """Initialize the use case.

        Args:
            routes: Repository used to allocate and persist routes.
            authz: Service used for authorization checks.
        """
        super().__init__(authz)
        self._routes = routes

    @requires(
        Permission.ROUTE_CREATE,
        operation=AuthorizationOperation.ROUTE_CREATE,
        target_resource_type=AuditResourceType.ROUTE,
        target_resource_id_resolver=None,
    )
    def execute(self, command: CreateRouteCommand) -> DeliveryRoute:
        """Create and persist a delivery route.

        Args:
            command: Ordered raw route locations and optional business-local
                departure time.

        Returns:
            The newly created route.

        Raises:
            PermissionError: If the caller lacks route creation permission.
            DatabaseError: If the route creation persistence fails.
            DomainValidationError: If the route has too few stops or contains invalid locations.
        """
        route = self._routes.create(
            locations=command.locations,
            departure_time=command.departure_time,
        )
        logger.info(
            "Created route %d from %s to %s with %d stops.",
            route.route_id,
            route.start_location,
            route.end_location,
            len(route.locations),
        )
        self.track_domain_recorder(route)
        return route
