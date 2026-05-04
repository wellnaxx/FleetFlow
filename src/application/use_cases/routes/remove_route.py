"""Use case for removing a route from runtime state."""

from src.domain.entities.delivery_route import DeliveryRoute
from src.ports.output.package_repository import PackageRepositoryPort
from src.ports.output.route_repository import RouteRepositoryPort
from src.ports.output.truck_repository import TruckRepositoryPort


class RemoveRouteUseCase:
    """Remove a route and detach its packages and truck."""

    def __init__(
        self, routes: RouteRepositoryPort, packages: PackageRepositoryPort, trucks: TruckRepositoryPort
    ) -> None:
        """Initialize the use case.

        Args:
            routes: Repository used to fetch and remove routes.
            packages: Repository used to update package state.
            trucks: Repository used to update truck state.
        """
        self._routes = routes
        self._packages = packages
        self._trucks = trucks

    def execute(self, route_id: int) -> DeliveryRoute:
        """Remove a route by id.

        Args:
            route_id: Identifier of the route to remove.

        Returns:
            The removed route entity.

        Raises:
            ValueError: If the route does not exist.
        """
        route = self._routes.get_by_id(route_id)
        if not route:
            raise ValueError(f"Route with ID {route_id} not found")

        for package in list(route.packages):
            route.detach_package(package)
            self._packages.update_state(package)

        truck = route.truck
        route.release_truck(force=True)
        if truck is not None:
            self._trucks.update_state(truck)

        self._routes.remove(route_id)
        return route
