"""Use case for removing a route from runtime state."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.application.exceptions.application_errors import NotFoundError
from src.application.services.authorization_service import AuthorizationService, requires_all
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.enums.auth import Permission

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from src.domain.entities.delivery_package import DeliveryPackage, DeliveryPackageStateSnapshot
    from src.domain.entities.delivery_route import RouteStateSnapshot
    from src.domain.entities.truck import Truck, TruckStateSnapshot
    from src.ports.output.route_repository import RouteRepositoryPort
    from src.ports.output.unit_of_work import UnitOfWorkPort


@dataclass(frozen=True)
class _RouteRemovalSnapshot:
    route: RouteStateSnapshot
    packages: tuple[tuple[DeliveryPackage, DeliveryPackageStateSnapshot], ...]
    truck: Truck | None
    truck_state: TruckStateSnapshot | None


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
            PermissionError: If the caller lacks route removal permission.
            DatabaseError: If the route removal persistence fails.
            NotFoundError: If the route does not exist.
        """
        route = self._get_route(route_id)
        snapshot = self._snapshot_removal_state(route)
        package_count = len(route.packages)
        truck = route.truck
        truck_id = truck.vehicle_id if truck is not None else None

        try:
            detached_packages = self._detach_route_state(route)
            self._persist_removal(
                route_id=route_id,
                detached_packages=detached_packages,
                truck=truck,
            )
        except Exception:
            self._restore_removal_state(route, snapshot)
            raise

        logger.info(
            "Removed route %d and detached %d package(s); released truck_id=%s.",
            route_id,
            package_count,
            truck_id,
        )
        return route

    def _get_route(self, route_id: int) -> DeliveryRoute:
        route = self._routes.get_by_id(route_id)
        if not route:
            logger.warning("Route removal requested for missing route %d.", route_id)
            raise NotFoundError(f"Route with ID {route_id} not found")
        return route

    def _snapshot_removal_state(self, route: DeliveryRoute) -> _RouteRemovalSnapshot:
        truck = route.truck
        return _RouteRemovalSnapshot(
            route=route.snapshot_state(),
            packages=tuple((package, package.snapshot_state()) for package in route.packages),
            truck=truck,
            truck_state=truck.snapshot_state() if truck is not None else None,
        )

    def _detach_route_state(self, route: DeliveryRoute) -> list[DeliveryPackage]:
        detached_packages: list[DeliveryPackage] = []
        for package in list(route.packages):
            route.detach_package(package)
            detached_packages.append(package)

        route.release_truck(force=True)
        return detached_packages

    def _persist_removal(
        self,
        route_id: int,
        detached_packages: list[DeliveryPackage],
        truck: Truck | None,
    ) -> None:
        with self._unit_of_work as uow:
            for package in detached_packages:
                uow.packages.update_state(package)

            if truck is not None:
                uow.trucks.update_state(truck)

            uow.routes.remove(route_id)
            uow.commit()

    def _restore_removal_state(self, route: DeliveryRoute, snapshot: _RouteRemovalSnapshot) -> None:
        route.restore_state(snapshot.route)
        for package, package_snapshot in snapshot.packages:
            package.restore_state(package_snapshot)
        if snapshot.truck is not None and snapshot.truck_state is not None:
            snapshot.truck.restore_state(snapshot.truck_state)
