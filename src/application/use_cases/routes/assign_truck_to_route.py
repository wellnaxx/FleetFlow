"""Use case for assigning a truck to a route."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.application.exceptions.application_errors import ConflictError, NotFoundError
from src.application.services.authorization_service import AuthorizationService, requires
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.domain.enums.auth import Permission

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from datetime import datetime

    from src.domain.entities.delivery_route import DeliveryRoute
    from src.domain.entities.truck import Truck
    from src.domain.value_objects.location_code import LocationCode
    from src.ports.output.route_repository import RouteRepositoryPort
    from src.ports.output.unit_of_work import UnitOfWorkPort
    from src.ports.output.vehicle_manager import VehicleManagerPort


@dataclass(frozen=True, slots=True)
class _RouteSuitabilityProbe:
    total_distance_km: int
    start_location: LocationCode
    departure_time: datetime
    assigned_weight: float

    def total_assigned_weight(self) -> float:
        """Return package weight assigned to the probed route."""
        return self.assigned_weight

    def maximum_segment_load(self) -> float:
        """Return maximum segment load for the probed route."""
        return self.assigned_weight


@dataclass(frozen=True, slots=True)
class AssignTruckToRouteResult:
    """Result returned after a truck is assigned to a route."""

    route_id: int
    truck_id: int


class AssignTruckToRouteUseCase(AuthorizedUseCase[AssignTruckToRouteResult]):
    """Assign a truck to a route after suitability checks."""

    def __init__(
        self,
        routes: RouteRepositoryPort,
        vehicle_manager: VehicleManagerPort,
        unit_of_work: UnitOfWorkPort,
        authz: AuthorizationService,
    ) -> None:
        """Initialize assignment dependencies.

        Args:
            routes: Repository used to fetch the target route.
            vehicle_manager: Vehicle manager used to fetch and validate trucks.
            unit_of_work: Transaction boundary used to persist route and truck
                state together after assignment.
            authz: Service used for authorization checks.
        """
        super().__init__(authz)
        self._routes = routes
        self._vehicle_manager = vehicle_manager
        self._unit_of_work = unit_of_work

    @requires(Permission.ROUTE_ASSIGN_TRUCK)
    def execute(self, truck_id: int, route_id: int, now: datetime) -> AssignTruckToRouteResult:
        """Assign a truck to a route.

        Args:
            truck_id: Identifier of the truck to assign.
            route_id: Identifier of the route to update.
            now: Clock value used when scheduling an unscheduled route.

        Returns:
            A summary of the successful truck assignment.

        Raises:
            PermissionError: If the caller lacks truck assignment permission.
            DatabaseError: If the truck assignment persistence fails.
            NotFoundError: If the requested resource is not found.
            ConflictError: If the selected route already has a truck assigned
                or the selected truck is not suitable for the route.
        """
        route = self._get_route(route_id)
        truck = self._get_truck(truck_id, route_id)

        self._ensure_route_has_no_truck(route)
        self._ensure_truck_is_suitable(truck=truck, route=route, now=now)
        self._assign_and_persist(route=route, truck=truck, now=now)

        logger.info("Assigned truck %d to route %d.", truck.vehicle_id, route.route_id)
        return AssignTruckToRouteResult(route_id=route.route_id, truck_id=truck.vehicle_id)

    def _get_route(self, route_id: int) -> DeliveryRoute:
        route = self._routes.get_by_id(route_id)
        if route is None:
            logger.warning("Truck assignment requested for missing route %d.", route_id)
            raise NotFoundError(f"Route with ID {route_id} not found")
        return route

    def _get_truck(self, truck_id: int, route_id: int) -> Truck:
        truck = self._vehicle_manager.find_by_id(truck_id)
        if truck is None:
            logger.warning("Truck assignment requested with missing truck %d for route %d.", truck_id, route_id)
            raise NotFoundError(f"Truck with ID {truck_id} not found")
        return truck

    def _ensure_route_has_no_truck(self, route: DeliveryRoute) -> None:
        current_truck = route.truck
        if current_truck is None:
            return

        logger.warning(
            "Truck assignment rejected because route %d already has truck %d.",
            route.route_id,
            current_truck.vehicle_id,
        )
        raise ConflictError(f"Route {route.route_id} already has truck {current_truck.vehicle_id} assigned")

    def _route_for_suitability(
        self, route: DeliveryRoute, now: datetime
    ) -> DeliveryRoute | _RouteSuitabilityProbe:
        if route.departure_time is None:
            return _RouteSuitabilityProbe(
                total_distance_km=route.total_distance_km,
                start_location=route.start_location,
                departure_time=now,
                assigned_weight=route.maximum_segment_load(),
            )
        return route

    def _ensure_truck_is_suitable(self, truck: Truck, route: DeliveryRoute, now: datetime) -> None:
        effective_route = self._route_for_suitability(route, now)
        ok, reason = self._vehicle_manager.is_suitable_for_route(truck, effective_route)
        if ok:
            return

        logger.warning("Truck %d rejected for route %d: %s.", truck.vehicle_id, route.route_id, reason)
        raise ConflictError(
            f"Truck {truck.vehicle_id} is not suitable for route {route.route_id}: {reason}. "
            f"Query suitable trucks for this route to see available options."
        )

    def _assign_and_persist(self, route: DeliveryRoute, truck: Truck, now: datetime) -> None:
        route_snapshot = route.snapshot_state()
        truck_snapshot = truck.snapshot_state()
        try:
            self._assign_in_memory(route=route, truck=truck, now=now)
            self._persist_assignment(route=route, truck=truck)
        except Exception:
            route.restore_state(route_snapshot)
            truck.restore_state(truck_snapshot)
            raise

    def _assign_in_memory(self, route: DeliveryRoute, truck: Truck, now: datetime) -> None:
        if route.departure_time is None:
            route.schedule(now)
        route.truck = truck
        truck.assign(route)

    def _persist_assignment(self, route: DeliveryRoute, truck: Truck) -> None:
        with self._unit_of_work as uow:
            uow.routes.update_state(route)
            uow.trucks.update_state(truck)
            uow.commit()
