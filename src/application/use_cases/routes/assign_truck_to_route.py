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
    from src.domain.value_objects.location_code import LocationCode
    from src.ports.output.route_repository import RouteRepositoryPort
    from src.ports.output.unit_of_work import UnitOfWorkPort
    from src.ports.output.vehicle_manager import VehicleManagerPort


@dataclass(frozen=True)
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


@dataclass(frozen=True)
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
        route = self._routes.get_by_id(route_id)
        if route is None:
            logger.warning("Truck assignment requested for missing route %d.", route_id)
            raise NotFoundError(f"Route with ID {route_id} not found")

        truck = self._vehicle_manager.find_by_id(truck_id)
        if not truck:
            logger.warning("Truck assignment requested with missing truck %d for route %d.", truck_id, route_id)
            raise NotFoundError(f"Truck with ID {truck_id} not found")

        current_truck = route.truck
        if current_truck is not None:
            logger.warning(
                "Truck assignment rejected because route %d already has truck %d.",
                route_id,
                current_truck.vehicle_id,
            )
            raise ConflictError(f"Route {route_id} already has truck {current_truck.vehicle_id} assigned")

        effective_route: DeliveryRoute | _RouteSuitabilityProbe = route
        if route.departure_time is None:
            effective_route = _RouteSuitabilityProbe(
                total_distance_km=route.total_distance_km,
                start_location=route.start_location,
                departure_time=now,
                assigned_weight=route.maximum_segment_load(),
            )

        ok, reason = self._vehicle_manager.is_suitable_for_route(truck, effective_route)
        if not ok:
            logger.warning("Truck %d rejected for route %d: %s.", truck_id, route_id, reason)
            raise ConflictError(
                f"Truck {truck_id} is not suitable for route {route_id}: {reason}. "
                f"Query suitable trucks for this route to see available options."
            )

        route_snapshot = route.snapshot_state()
        truck_snapshot = truck.snapshot_state()
        try:
            if route.departure_time is None:
                route.schedule(now)
            route.truck = truck
            truck.assign(route)

            with self._unit_of_work as uow:
                uow.routes.update_state(route)
                uow.trucks.update_state(truck)
                uow.commit()
        except Exception:
            route.restore_state(route_snapshot)
            truck.restore_state(truck_snapshot)
            raise

        logger.info("Assigned truck %d to route %d.", truck.vehicle_id, route.route_id)
        return AssignTruckToRouteResult(route_id=route.route_id, truck_id=truck.vehicle_id)
