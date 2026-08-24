"""Use case for finding trucks suitable for a route."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.authorization_operations import AuthorizationOperation
from src.application.exceptions.application_errors import NotFoundError
from src.application.services.authorization_service import AuthorizationService, requires
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.domain.entities.truck import Truck
from src.domain.enums.auth import Permission

if TYPE_CHECKING:
    from src.application.queries.routes.find_suitable_trucks_for_route import (
        FindSuitableTrucksForRouteQuery,
    )
    from src.ports.output.route_repository import RouteRepositoryPort
    from src.ports.output.vehicle_manager import VehicleManagerPort


def _resolve_route_target_id(
    _self: FindSuitableTrucksForRouteUseCase,
    query: FindSuitableTrucksForRouteQuery,
) -> int | None:
    """Resolve the audit target resource id for a finding suitable trucks for a route attempt."""
    return query.route_id


class FindSuitableTrucksForRouteUseCase(AuthorizedUseCase[list[Truck]]):
    """Find suitable trucks through the published application query contract."""

    def __init__(
        self, routes: RouteRepositoryPort, vehicles: VehicleManagerPort, authz: AuthorizationService
    ) -> None:
        """Initialize suitability dependencies.

        Args:
            routes: Repository used to fetch the route.
            vehicles: Vehicle manager used to evaluate trucks.
            authz: Service used for authorization checks.
        """
        super().__init__(authz)
        self._routes = routes
        self._vehicles = vehicles

    @requires(
        Permission.ROUTE_FIND_TRUCK_FOR,
        operation=AuthorizationOperation.ROUTE_FIND_SUITABLE_TRUCKS,
        target_resource_type=AuditResourceType.ROUTE,
        target_resource_id_resolver=_resolve_route_target_id,
    )
    def execute(self, query: FindSuitableTrucksForRouteQuery) -> list[Truck]:
        """Return trucks that are currently suitable for a route.

        Args:
            query: Route identifier to evaluate against available trucks.

        Returns:
            A list of suitable trucks.

        Raises:
            PermissionError: If the caller lacks suitable-truck lookup permission.
            DatabaseError: If suitable truck persistence lookup fails.
            NotFoundError: If the route does not exist.
        """
        route_id = query.route_id
        route = self._routes.get_by_id(route_id)
        if route is None:
            raise NotFoundError(f"Route with ID {route_id} not found")
        return self._vehicles.find_available_for_route(route)
