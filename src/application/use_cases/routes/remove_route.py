"""Use case for removing a route from runtime state."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.application.services.authorization_service import AuthorizationService, requires_all
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.enums.auth import Permission

if TYPE_CHECKING:
    from src.domain.entities.delivery_package import DeliveryPackage
    from src.ports.output.route_repository import RouteRepositoryPort
    from src.ports.output.unit_of_work import UnitOfWorkPort


class RemoveRouteUseCase(AuthorizedUseCase[DeliveryRoute]):
    """Remove a route and detach its packages and truck."""

    def __init__(
        self,
        routes: RouteRepositoryPort,
        unit_of_work: UnitOfWorkPort,
        authz: AuthorizationService,
    ) -> None:
        """Initialize the use case.

        Args:
            routes: Repository used to fetch the target route.
            unit_of_work: Transaction boundary used to persist package and truck
                state together with route removal.
            authz: Service used for authorization checks.
        """
        super().__init__(authz)
        self._routes = routes
        self._unit_of_work = unit_of_work

    @requires_all(Permission.ROUTE_REMOVE, Permission.ROUTE_VIEW)
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

        route_snapshot = route.snapshot_state()
        package_snapshots = [(package, package.snapshot_state()) for package in route.packages]
        truck = route.truck
        truck_snapshot = truck.snapshot_state() if truck is not None else None
        detached_packages: list[DeliveryPackage] = []
        try:
            for package in list(route.packages):
                route.detach_package(package)
                detached_packages.append(package)

            route.release_truck(force=True)
            with self._unit_of_work as uow:
                for package in detached_packages:
                    uow.packages.update_state(package)

                if truck is not None:
                    uow.trucks.update_state(truck)

                uow.routes.remove(route_id)

                uow.commit()
        except Exception:
            route.restore_state(route_snapshot)
            for package, snapshot in package_snapshots:
                package.restore_state(snapshot)
            if truck is not None and truck_snapshot is not None:
                truck.restore_state(truck_snapshot)
            raise
        return route
