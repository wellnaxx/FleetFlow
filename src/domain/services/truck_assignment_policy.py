"""Pure domain policy for truck-to-route assignment suitability."""

from datetime import datetime
from typing import Protocol

from src.domain.entities.truck import Truck
from src.domain.enums.truck_assignment_rejection_reasons import TruckAssignmentRejectionReason
from src.domain.value_objects.location_code import LocationCode
from src.domain.value_objects.truck_assignment_decision import TruckAssignmentDecision


class RouteSuitabilityView(Protocol):
    """Expose only the route state needed by truck assignment policy."""

    @property
    def total_distance_km(self) -> int:
        """Total route distance in kilometers."""
        ...

    @property
    def start_location(self) -> LocationCode:
        """Route origin location."""
        ...

    @property
    def departure_time(self) -> datetime | None:
        """Scheduled departure time, or ``None`` when unscheduled."""
        ...

    def maximum_segment_load(self) -> float:
        """Return the heaviest package load carried on any route segment."""
        ...


class TruckAssignmentPolicy:
    """Evaluate whether a fleet truck can serve a route."""

    @staticmethod
    def evaluate(*, truck: Truck, route: RouteSuitabilityView) -> TruckAssignmentDecision:
        """Check structural and schedule suitability for assigning a truck.

        Args:
            truck: Candidate truck.
            route: Route view used for segment capacity, range, location, and
                timing checks.

        Returns:
            Structured acceptance or rejection decision. Rejections include a
            stable reason and a human-readable explanation.
        """
        if truck.max_range < route.total_distance_km:
            return TruckAssignmentDecision.reject(
                reason=TruckAssignmentRejectionReason.TRUCK_RANGE_INSUFFICIENT,
                message="range too short",
            )
        if truck.capacity < route.maximum_segment_load():
            return TruckAssignmentDecision.reject(
                reason=TruckAssignmentRejectionReason.TRUCK_CAPACITY_INSUFFICIENT,
                message="insufficient capacity",
            )
        current_route = truck.route
        if current_route is None:
            if truck.current_location != route.start_location:
                return TruckAssignmentDecision.reject(
                    reason=TruckAssignmentRejectionReason.TRUCK_AT_WRONG_LOCATION,
                    message=f"wrong location ({truck.current_location} != {route.start_location})",
                )
            return TruckAssignmentDecision.accept()

        if route.departure_time is None:
            return TruckAssignmentDecision.reject(
                reason=TruckAssignmentRejectionReason.TARGET_ROUTE_UNSCHEDULED,
                message="route not scheduled yet",
            )

        current_eta = current_route.eta_final
        if current_eta is None:
            return TruckAssignmentDecision.reject(
                reason=TruckAssignmentRejectionReason.CURRENT_ROUTE_AVAILABILITY_UNKNOWN,
                message="truck already assigned to a route with unknown availability",
            )

        if current_eta >= route.departure_time:
            return TruckAssignmentDecision.reject(
                reason=TruckAssignmentRejectionReason.AVAILABILITY_WINDOW_OVERLAP,
                message="truck busy in the requested time window",
            )

        availability_location = current_route.end_location
        if availability_location != route.start_location:
            return TruckAssignmentDecision.reject(
                reason=TruckAssignmentRejectionReason.TRUCK_AT_WRONG_LOCATION,
                message=f"wrong availability location ({availability_location} != {route.start_location})",
            )

        return TruckAssignmentDecision.accept()
