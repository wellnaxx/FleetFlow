"""Domain policy for evaluating package-to-route assignment candidates."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.domain.enums.package_assignment_rejection_reasons import PackageAssignmentRejectionReason
from src.domain.value_objects.package_assignment_decision import PackageAssignmentDecision
from src.domain.value_objects.route_schedule import RoutePositionKind

if TYPE_CHECKING:
    from datetime import datetime

    from src.domain.entities.delivery_package import DeliveryPackage
    from src.domain.entities.delivery_route import DeliveryRoute
    from src.domain.value_objects.location_code import LocationCode


class PackageAssignmentPolicy:
    """Evaluate route compatibility, pickup progress, and truck constraints."""

    @classmethod
    def evaluate(
        cls,
        *,
        route: DeliveryRoute,
        package: DeliveryPackage,
        now: datetime | None = None,
    ) -> PackageAssignmentDecision:
        """Evaluate whether a package can be assigned to the provided route.

        Args:
            route: Target route to which the package will be assigned to.
            package: Package being evaluated.
            now: Clock value used for live pickup-pass validation.

        Returns:
            Structured acceptance or first applicable rejection decision.
        """
        location_indices = {location: index for index, location in enumerate(route.locations)}

        decision = cls._evaluate_package_route_compatibility(
            location_indices,
            route,
            package,
        )
        if not decision.accepted:
            return decision

        decision = cls._evaluate_pickup_not_passed(
            location_indices,
            route,
            package,
            now,
        )
        if not decision.accepted:
            return decision

        decision = cls._evaluate_truck_constraints(route, package)
        if not decision.accepted:
            return decision

        return PackageAssignmentDecision.accept()

    @staticmethod
    def _evaluate_package_route_compatibility(
        location_indices: dict[LocationCode, int], route: DeliveryRoute, package: DeliveryPackage
    ) -> PackageAssignmentDecision:
        """Evaluate whether the route visits the package endpoints in order."""
        if package.start_location not in location_indices or package.end_location not in location_indices:
            return PackageAssignmentDecision.reject(
                reason=PackageAssignmentRejectionReason.LOCATIONS_NOT_ON_ROUTE,
                message=f"Route {route.route_id} does not include start/end of "
                f"package {package.package_id} ({package.start_location} -> {package.end_location}).",
            )

        if not route.includes_in_order(package.start_location, package.end_location):
            return PackageAssignmentDecision.reject(
                reason=PackageAssignmentRejectionReason.LOCATIONS_OUT_OF_ORDER,
                message=f"Route {route.route_id} does not pass from {package.start_location} "
                f"to {package.end_location} in order for package {package.package_id}.",
            )

        return PackageAssignmentDecision.accept()

    @staticmethod
    def _evaluate_pickup_not_passed(
        location_indices: dict[LocationCode, int],
        route: DeliveryRoute,
        package: DeliveryPackage,
        now: datetime | None,
    ) -> PackageAssignmentDecision:
        """Reject assignment after route progress has passed the pickup stop."""
        if route.departure_time is None:
            return PackageAssignmentDecision.accept()

        pickup_index = location_indices[package.start_location]
        position = route.current_position(now)

        if position.kind in {RoutePositionKind.UNSCHEDULED, RoutePositionKind.BEFORE_START}:
            return PackageAssignmentDecision.accept()

        if position.kind == RoutePositionKind.AT_STOP:
            stop_city = position.stop_city
            if stop_city and location_indices[stop_city] > pickup_index:
                return PackageAssignmentPolicy._pickup_passed_error(route, package)
            return PackageAssignmentDecision.accept()

        if position.kind == RoutePositionKind.IN_TRANSIT:
            from_city = position.from_city
            if from_city and location_indices[from_city] >= pickup_index:
                return PackageAssignmentPolicy._pickup_passed_error(route, package)
            return PackageAssignmentDecision.accept()

        if position.kind == RoutePositionKind.AFTER_END:
            return PackageAssignmentPolicy._pickup_passed_error(route, package)

        return PackageAssignmentDecision.accept()

    @staticmethod
    def _pickup_passed_error(route: DeliveryRoute, package: DeliveryPackage) -> PackageAssignmentDecision:
        """Build the standard pickup-passed rejection decision."""
        return PackageAssignmentDecision.reject(
            reason=PackageAssignmentRejectionReason.PICKUP_ALREADY_PASSED,
            message=f"Route {route.route_id} has already passed pickup location "
            f"{package.start_location} for package {package.package_id}.",
        )

    @staticmethod
    def _evaluate_truck_constraints(
        route: DeliveryRoute, extra_package: DeliveryPackage
    ) -> PackageAssignmentDecision:
        """Evaluate candidate segment load and route range against the assigned truck."""
        if route.truck is None:
            return PackageAssignmentDecision.accept()
        max_segment_load = PackageAssignmentPolicy.maximum_segment_load(
            locations=tuple(route.locations), packages=route.packages, extra_package=extra_package
        )
        if max_segment_load > route.truck.capacity:
            return PackageAssignmentDecision.reject(
                reason=PackageAssignmentRejectionReason.TRUCK_CAPACITY_EXCEEDED,
                message=f"Truck {route.truck.vehicle_id} capacity exceeded: "
                f"segment load {max_segment_load}kg > {route.truck.capacity}kg.",
            )

        if route.truck.max_range < route.total_distance_km:
            return PackageAssignmentDecision.reject(
                reason=PackageAssignmentRejectionReason.TRUCK_RANGE_INSUFFICIENT,
                message=f"Truck {route.truck.vehicle_id} lacks range for {route.total_distance_km} km "
                f"(range: {route.truck.max_range} km).",
            )

        return PackageAssignmentDecision.accept()

    @staticmethod
    def maximum_segment_load(
        *,
        locations: tuple[LocationCode, ...],
        packages: tuple[DeliveryPackage, ...],
        extra_package: DeliveryPackage | None = None,
    ) -> float:
        """Return the heaviest cargo load carried on any route segment.

        Capacity is constrained by the maximum simultaneous load between two
        adjacent stops, not by the sum of every package assigned to the whole
        route. `extra_package` is included as a candidate load without mutating
        route state.

        Args:
            locations: Ordered route locations used to identify segment spans.
            packages: Packages already assigned to the route.
            extra_package: Optional package being evaluated for assignment.

        Returns:
            Maximum carried weight across all adjacent route segments.
        """
        indices = {location: index for index, location in enumerate(locations)}
        segment_loads = [0.0] * (len(locations) - 1)

        candidates = packages
        if extra_package is not None:
            candidates = (*candidates, extra_package)

        for package in candidates:
            start_index = indices.get(package.start_location)
            end_index = indices.get(package.end_location)

            if start_index is None or end_index is None or start_index >= end_index:
                continue

            for segment_index in range(start_index, end_index):
                segment_loads[segment_index] += package.weight

        return max(segment_loads, default=0.0)
