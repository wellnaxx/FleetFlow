"""Use case for finding trucks suitable for a route."""

from src.application.exceptions.application_errors import NotFoundError
from src.application.services.authorization_service import AuthorizationService, requires
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.domain.entities.truck import Truck
from src.domain.enums.auth import Permission
from src.ports.output.route_repository import RouteRepositoryPort
from src.ports.output.vehicle_manager import VehicleManagerPort


class FindSuitableTrucksForRouteUseCase(AuthorizedUseCase[list[Truck]]):
    """Find trucks that can serve a route."""

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

    @requires(Permission.ROUTE_FIND_TRUCK_FOR)
    def execute(self, route_id: int) -> list[Truck]:
        """Return trucks that are currently suitable for a route.

        Args:
            route_id: Identifier of the route to evaluate.

        Returns:
            A list of suitable trucks.

        Raises:
            PermissionError: If the caller lacks suitable-truck lookup permission.
            DatabaseError: If suitable truck persistence lookup fails.
            NotFoundError: If the route does not exist.
        """
        route = self._routes.get_by_id(route_id)
        if route is None:
            raise NotFoundError(f"Route with ID {route_id} not found")
        return self._vehicles.find_available_for_route(route)
