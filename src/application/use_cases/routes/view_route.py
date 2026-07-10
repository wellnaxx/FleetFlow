"""Use case for viewing one route."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.authorization_operations import AuthorizationOperation
from src.application.exceptions.application_errors import NotFoundError
from src.application.services.authorization_service import AuthorizationService, requires
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.enums.auth import Permission

if TYPE_CHECKING:
    from src.ports.output.route_repository import RouteRepositoryPort


def _resolve_route_target_id(
    _self: ViewRouteUseCase,
    route_id: int,
) -> int | None:
    """Resolve the audit target resource id for a route view attempt."""
    return route_id


class ViewRouteUseCase(AuthorizedUseCase[DeliveryRoute]):
    """Fetch one route by id."""

    def __init__(self, routes: RouteRepositoryPort, authz: AuthorizationService) -> None:
        """Initialize the use case.

        Args:
            routes: Repository used to fetch routes.
            authz: Service used for authorization checks.
        """
        super().__init__(authz)
        self._routes = routes

    @requires(
        Permission.ROUTE_VIEW,
        operation=AuthorizationOperation.ROUTE_VIEW,
        target_resource_type=AuditResourceType.ROUTE,
        target_resource_id_resolver=_resolve_route_target_id,
    )
    def execute(self, route_id: int) -> DeliveryRoute:
        """Return one route by id.

        Args:
            route_id: Identifier of the route to fetch.

        Returns:
            The matching route entity.

        Raises:
            PermissionError: If the caller lacks route view permission.
            DatabaseError: If the route lookup persistence fails.
            NotFoundError: If the route does not exist.
        """
        route = self._routes.get_by_id(route_id)
        if not route:
            raise NotFoundError(f"Route with ID {route_id} not found")
        return route
