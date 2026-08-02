"""Runtime reconciliation of routes, packages, and truck state."""

import contextlib
import logging
from datetime import datetime
from typing import TYPE_CHECKING

from src.application.enums.package_reconciliation_reasons import PackageReconciliationReason
from src.application.enums.route_reconciliation_reasons import RouteReconciliationReason
from src.application.events.reconciliation_events import (
    PackageStateReconciled,
    RouteStateReconciled,
    TruckPositionReconciled,
    TruckRouteReferenceReconciled,
)
from src.application.results.heartbeat_summary_result import HeartbeatSummary
from src.application.results.truck_reconciliation_summary_result import TruckReconciliationSummary
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.entities.delivery_route import DeliveryRoute, RoutePosition, RoutePositionKind
from src.domain.entities.truck import Truck
from src.domain.enums.item_status import ItemStatus
from src.domain.enums.route_status import RouteStatus
from src.domain.enums.truck_release_reasons import TruckReleaseReason
from src.domain.value_objects.location_code import LocationCode

if TYPE_CHECKING:
    from src.application.events.base import ApplicationEvent

logger = logging.getLogger(__name__)


class WorldStateReconciliationService:
    """Derive current world state from route schedules and package assignments."""

    def reconcile_routes(
        self,
        routes: list[DeliveryRoute],
        now: datetime | None = None,
        *,
        update_trucks: bool = True,
    ) -> HeartbeatSummary:
        """Reconcile route status, package state, and optional truck state.

        Args:
            routes: Routes to reconcile.
            now: Optional reconciliation time. Defaults to current time.
            update_trucks: Whether truck runtime state should be mutated.

        Returns:
            Summary of entity changes and direct-reconciliation events.

        Notes:
            A route that cannot be reconciled is restored to its pre-attempt
            state and logged. Reconciliation then continues with later routes.
        """
        current_time = now or datetime.now()
        reconciliation_events: list[ApplicationEvent] = []

        routes_updated: list[DeliveryRoute] = []
        packages_updated: list[DeliveryPackage] = []
        trucks_moved: list[Truck] = []
        trucks_released: list[Truck] = []
        trucks_reconciled: list[Truck] = []

        for route in routes:
            route_snapshot = route.snapshot_state()
            route_event_checkpoint = route.event_checkpoint()
            package_snapshots = tuple(
                (package, package.snapshot_state(), package.event_checkpoint()) for package in route.packages
            )
            original_truck = route.truck
            truck_snapshot = original_truck.snapshot_state() if original_truck is not None else None

            route_changed = False
            route_events: list[ApplicationEvent] = []
            truck_summary = TruckReconciliationSummary()
            package_changes: list[DeliveryPackage] = []
            package_events: list[PackageStateReconciled] = []

            try:
                new_status, reason = self._compute_route_status(route, current_time)
                if route.status != new_status:
                    event = self._apply_route_status(route, new_status, reason, current_time)
                    if event is not None:
                        route_events.append(event)
                    route_changed = True

                if update_trucks:
                    truck_summary = self._reconcile_truck_for_route(route, current_time)

                package_changes, package_events = self._update_packages_for_route(
                    route,
                    current_time,
                )
            except Exception:
                route.restore_state(route_snapshot)
                route.restore_event_checkpoint(route_event_checkpoint)

                for package, package_snapshot, package_event_checkpoint in package_snapshots:
                    package.restore_state(package_snapshot)
                    package.restore_event_checkpoint(package_event_checkpoint)

                if original_truck is not None and truck_snapshot is not None:
                    original_truck.restore_state(truck_snapshot)

                logger.exception(
                    "Failed to reconcile route %s; restored route state and continuing.",
                    route.route_id,
                )
                continue

            if route_changed:
                routes_updated.append(route)
            reconciliation_events.extend(route_events)
            reconciliation_events.extend(truck_summary.events)
            trucks_moved.extend(truck_summary.trucks_moved)
            trucks_released.extend(truck_summary.trucks_released)
            trucks_reconciled.extend(truck_summary.trucks_reconciled)
            packages_updated.extend(package_changes)
            reconciliation_events.extend(package_events)

        return HeartbeatSummary(
            mutated_routes=tuple(routes_updated),
            mutated_packages=tuple(packages_updated),
            mutated_trucks_moved=tuple(trucks_moved),
            mutated_trucks_released=tuple(trucks_released),
            mutated_trucks_reconciled=tuple(trucks_reconciled),
            reconciliation_events=tuple(reconciliation_events),
        )

    def _reconcile_truck_for_route(
        self,
        route: DeliveryRoute,
        now: datetime,
    ) -> TruckReconciliationSummary:
        """Reconcile one route's truck relationship and schedule position.

        Args:
            route: Route whose assigned truck should be reconciled.
            now: Business time used to derive the route position.

        Returns:
            Truck mutations and direct-reconciliation events for the route.

        Raises:
            RuntimeError: If the route and truck reference different assignments
                or a completed route lacks a final ETA.
        """
        events: list[TruckPositionReconciled | TruckRouteReferenceReconciled] = []
        trucks_reconciled: list[Truck] = []

        truck = route.truck
        if truck is None:
            return TruckReconciliationSummary()

        if truck.route is None:
            truck.route = route
            events.append(
                TruckRouteReferenceReconciled(
                    truck_id=truck.vehicle_id,
                    previous_route_id=None,
                    new_route_id=truck.route.route_id,
                    occurred_at=now,
                )
            )
            trucks_reconciled.append(truck)

        elif truck.route is not route:
            raise RuntimeError(
                f"Route {route.route_id} references truck {truck.vehicle_id}, "
                "but the truck does not reference that route."
            )

        # current_position() reports the exact final ETA as AT_STOP, while times after
        # the final ETA are AFTER_END. Both paths can release the truck, but they cover
        # different position states.
        position = route.current_position(now)

        before_location = truck.current_location
        before_in_transit_to = truck.in_transit_to

        trucks_moved: list[Truck] = []
        trucks_released: list[Truck] = []

        if position.kind == RoutePositionKind.UNSCHEDULED:
            if self._set_truck_unscheduled(truck):
                trucks_moved.append(truck)

        elif position.kind == RoutePositionKind.BEFORE_START:
            if self._set_truck_before_start(truck, route):
                trucks_moved.append(truck)

        elif position.kind == RoutePositionKind.AT_STOP:
            moved, released = self._set_truck_at_stop(
                truck=truck,
                route=route,
                position=position,
                now=now,
            )
            if moved:
                trucks_moved.append(truck)
            if released:
                trucks_released.append(truck)

        elif position.kind == RoutePositionKind.IN_TRANSIT:
            if self._set_truck_in_transit(truck, route, position):
                trucks_moved.append(truck)

        elif position.kind == RoutePositionKind.AFTER_END:
            completion_time = self._validate_route_eta_final(route)

            if route.release_truck(
                now=now, force=False, reason=TruckReleaseReason.ROUTE_COMPLETED, occurred_at=completion_time
            ):
                trucks_released.append(truck)

        after_location = truck.current_location
        after_in_transit_to = truck.in_transit_to
        position_changed = after_location != before_location or after_in_transit_to != before_in_transit_to

        if position_changed:
            if truck not in trucks_moved:
                trucks_moved.append(truck)

            events.append(
                TruckPositionReconciled(
                    truck_id=truck.vehicle_id,
                    route_id=route.route_id,
                    previous_location=before_location,
                    new_location=after_location,
                    previous_in_transit_to=before_in_transit_to,
                    new_in_transit_to=after_in_transit_to,
                    position_kind=position.kind,
                    occurred_at=now,
                )
            )

        return TruckReconciliationSummary(
            trucks_moved=tuple(trucks_moved),
            trucks_released=tuple(trucks_released),
            trucks_reconciled=tuple(trucks_reconciled),
            events=tuple(events),
        )

    def _validate_route_eta_final(self, route: DeliveryRoute) -> datetime:
        """Return the route's required final ETA.

        Args:
            route: Route expected to have a completion timestamp.

        Returns:
            The route's final expected-arrival time.

        Raises:
            RuntimeError: If the route has no final ETA.
        """
        completion_time = route.eta_final
        if completion_time is None:
            raise RuntimeError("Completed route has no completion time.")
        return completion_time

    def _compute_route_status(
        self, route: DeliveryRoute, now: datetime
    ) -> tuple[RouteStatus, RouteReconciliationReason | None]:
        """Derive route status and any reason needed for a direct correction.

        Args:
            route: Route whose schedule determines the desired status.
            now: Business time at which status is evaluated.

        Returns:
            Desired status and a correction reason. The reason is ``None`` for
            lifecycle transitions represented by domain events.
        """
        if route.departure_time is None:
            return RouteStatus.PLANNED, RouteReconciliationReason.MISSING_DEPARTURE_TIME

        if route.eta_final is None:
            return RouteStatus.SCHEDULED, RouteReconciliationReason.MISSING_EXPECTED_COMPLETION_TIME

        if now < route.departure_time:
            return RouteStatus.SCHEDULED, RouteReconciliationReason.BEFORE_SCHEDULED_DEPARTURE

        if now >= route.eta_final:
            return RouteStatus.COMPLETED, None

        return RouteStatus.IN_PROGRESS, None

    def _apply_route_status(
        self,
        route: DeliveryRoute,
        new_status: RouteStatus,
        reason: RouteReconciliationReason | None,
        occurred_at: datetime | None = None,
    ) -> RouteStateReconciled | None:
        """Apply a derived route status using lifecycle methods where possible.

        Args:
            route: Route to update.
            new_status: Schedule-derived status.
            reason: Reason for a direct status correction, if required.
            occurred_at: Time assigned to a direct reconciliation event.

        Returns:
            A reconciliation event for a direct correction, or ``None`` when a
            domain lifecycle method recorded the transition.

        Raises:
            RuntimeError: If required schedule evidence or a direct-correction
                reason is missing.
        """
        if new_status is RouteStatus.IN_PROGRESS:
            departure_time = route.departure_time
            if departure_time is None:
                raise RuntimeError("Started route has no departure time.")

            route.mark_started(occurred_at=departure_time)
            return None

        if new_status is RouteStatus.COMPLETED:
            completion_time = route.eta_final
            if completion_time is None:
                raise RuntimeError("Completed route has no completion time.")

            route.mark_completed(occurred_at=completion_time)
            return None

        if reason is None:
            raise RuntimeError("Direct route reconciliation requires a reason.")

        previous_status = route.status
        route.status = new_status
        return RouteStateReconciled(
            route_id=route.route_id,
            previous_status=previous_status,
            new_status=route.status,
            departure_time=route.departure_time,
            expected_completion_time=route.eta_final,
            reason=reason,
            occurred_at=occurred_at or datetime.now(),
        )

    def _set_truck_unscheduled(self, truck: Truck) -> bool:
        """Clear stale transit state for an unscheduled truck.

        Args:
            truck: Truck assigned to an unscheduled route.

        Returns:
            Whether the truck's transit target changed.
        """
        if truck.in_transit_to is None:
            return False

        truck.in_transit_to = None
        return True

    def _set_truck_before_start(self, truck: Truck, route: DeliveryRoute) -> bool:
        """Place a truck at its route origin before departure.

        Args:
            truck: Truck to reconcile.
            route: Assigned route providing the origin.

        Returns:
            Whether location or transit state changed.
        """
        moved = truck.current_location != route.start_location or truck.in_transit_to is not None
        truck.current_location = route.start_location
        truck.in_transit_to = None
        truck.route = route
        return moved

    def _set_truck_at_stop(
        self,
        truck: Truck,
        route: DeliveryRoute,
        position: RoutePosition,
        now: datetime,
    ) -> tuple[bool, bool]:
        """Place a truck at a reached stop and release it at route completion.

        Args:
            truck: Truck to reconcile.
            route: Assigned route.
            position: Schedule-derived stop position.
            now: Business time used to determine completion.

        Returns:
            A pair indicating whether the truck moved and whether it was released.

        Raises:
            RuntimeError: If a completed route lacks a final ETA.
        """
        moved = truck.current_location != position.stop_city or truck.in_transit_to is not None

        truck.current_location = position.stop_city
        truck.in_transit_to = None
        truck.route = route

        released = False

        if position.stop_city == route.end_location and route.eta_final is not None and now >= route.eta_final:
            completion_time = self._validate_route_eta_final(route)
            released = route.release_truck(
                now=now,
                force=False,
                reason=TruckReleaseReason.ROUTE_COMPLETED,
                occurred_at=completion_time,
            )

        return moved, released

    def _set_truck_in_transit(
        self,
        truck: Truck,
        route: DeliveryRoute,
        position: RoutePosition,
    ) -> bool:
        """Set a truck's current segment while its route is in transit.

        Args:
            truck: Truck to reconcile.
            route: Assigned route.
            position: Schedule-derived in-transit position.

        Returns:
            Whether location or transit-target state changed.
        """
        moved = False
        if position.from_city and truck.current_location != position.from_city:
            truck.current_location = position.from_city
            moved = True
        if truck.in_transit_to != position.to_city:
            moved = True
        truck.in_transit_to = position.to_city
        truck.route = route
        return moved

    def _update_packages_for_route(
        self,
        route: DeliveryRoute,
        now: datetime,
    ) -> tuple[list[DeliveryPackage], list[PackageStateReconciled]]:
        """Reconcile every package assigned to a route.

        One direct reconciliation event is produced per changed package, with
        all applicable correction reasons aggregated into that event. Domain
        lifecycle transitions continue to record their own domain events.

        Args:
            route: Route whose assigned packages should be reconciled.
            now: Business time used to derive package progress.

        Returns:
            Changed packages and their direct-reconciliation events.
        """
        changed_packages: list[DeliveryPackage] = []
        stop_times: dict[LocationCode, datetime] = {}
        events: list[PackageStateReconciled] = []

        if route.departure_time is not None:
            for city in route.locations:
                with contextlib.suppress(ValueError):
                    stop_times[city] = route.arrival_time_at(city)

        pos_index = {city: index for index, city in enumerate(route.locations)}

        for package in route.packages:
            package_changed = False
            reasons: list[PackageReconciliationReason] = []

            start = package.start_location
            end = package.end_location
            previous_status = package.status
            previous_location = package.current_location
            previous_expected_arrival = package.expected_arrival

            if route.departure_time is None:
                package_changed = self._restore_package_before_pickup(package)
                if package.expected_arrival is not None:
                    package.expected_arrival = None
                    reasons.append(PackageReconciliationReason.EXPECTED_ARRIVAL_RECALCULATED)
                    package_changed = True

                if package_changed:
                    reasons.append(PackageReconciliationReason.ROUTE_UNSCHEDULED)

                start_time = None
                end_time = None

            elif start not in pos_index or end not in pos_index or pos_index[start] > pos_index[end]:
                package_changed = self._restore_package_before_pickup(package)

                if package.expected_arrival is not None:
                    package.expected_arrival = None
                    reasons.append(PackageReconciliationReason.EXPECTED_ARRIVAL_RECALCULATED)
                    package_changed = True

                if package_changed:
                    reasons.append(PackageReconciliationReason.ROUTE_PATH_INVALID)

                start_time = None
                end_time = None
            else:
                start_time = stop_times.get(start)
                end_time = stop_times.get(end)

                if start_time and now < start_time:
                    package_changed = self._restore_package_before_pickup(package)

                    if package_changed:
                        reasons.append(PackageReconciliationReason.BEFORE_SCHEDULED_PICKUP)

                elif end_time and now >= end_time:
                    package_changed, reason = self._complete_package_lifecycle(
                        package,
                        pickup_time=start_time,
                        delivery_time=end_time,
                    )

                    if reason is not None:
                        reasons.append(reason)
                else:
                    package_changed, advance_reasons = self._advance_package_in_progress(
                        package,
                        pickup_time=start_time,
                        current_location=self._last_reached_city(
                            route,
                            start=start,
                            end=end,
                            stop_times=stop_times,
                            position_by_city=pos_index,
                            now=now,
                        ),
                    )

                    reasons.extend(advance_reasons)

                with contextlib.suppress(ValueError):
                    expected_arrival = route.arrival_time_at(end)
                    if package.expected_arrival != expected_arrival:
                        package.expected_arrival = expected_arrival
                        reasons.append(PackageReconciliationReason.EXPECTED_ARRIVAL_RECALCULATED)
                        package_changed = True

            if package_changed:
                changed_packages.append(package)

            if reasons:
                events.append(
                    PackageStateReconciled(
                        package_id=package.package_id,
                        route_id=route.route_id,
                        previous_status=previous_status,
                        new_status=package.status,
                        previous_location=previous_location,
                        new_location=package.current_location,
                        previous_expected_arrival=previous_expected_arrival,
                        new_expected_arrival=package.expected_arrival,
                        scheduled_pickup_time=start_time,
                        scheduled_delivery_time=end_time,
                        reasons=tuple(reasons),
                        occurred_at=now,
                    )
                )

        return changed_packages, events

    def _complete_package_lifecycle(
        self, package: DeliveryPackage, *, pickup_time: datetime | None, delivery_time: datetime
    ) -> tuple[bool, PackageReconciliationReason | None]:
        """Advance a package through any overdue pickup and delivery transitions.

        Args:
            package: Package whose delivery window has elapsed.
            pickup_time: Scheduled pickup time, if reconstructable.
            delivery_time: Scheduled delivery time used for the delivery event.

        Returns:
            Whether package state changed and an optional reason for a direct
            repair not represented by lifecycle events.
        """
        changed = False
        reason = None

        if package.status is ItemStatus.TODO:
            if pickup_time is None:
                # Missing schedule data prevents reconstructing the pickup event.
                # Repair the observed final state without inventing a timestamp.
                return self._set_package_state(
                    package,
                    status=ItemStatus.DONE,
                    current_location=package.end_location,
                ), PackageReconciliationReason.MISSING_PICKUP_TIME

            package.mark_picked_up(occurred_at=pickup_time)
            changed = True

        if package.status is ItemStatus.IN_PROGRESS:
            package.mark_delivered(occurred_at=delivery_time)
            changed = True

        if package.current_location != package.end_location:
            package.current_location = package.end_location
            changed = True
            reason = PackageReconciliationReason.LIFECYCLE_STATE_INCONSISTENT

        return changed, reason

    def _advance_package_in_progress(
        self,
        package: DeliveryPackage,
        *,
        pickup_time: datetime | None,
        current_location: LocationCode,
    ) -> tuple[bool, list[PackageReconciliationReason]]:
        """Reconcile a package within its active route window.

        Args:
            package: Package to advance or repair.
            pickup_time: Scheduled pickup time, if available.
            current_location: Last route city reached at reconciliation time.

        Returns:
            Whether package state changed and the direct-correction reasons.
        """
        changed = False
        reasons: list[PackageReconciliationReason] = []

        if package.status is ItemStatus.TODO and pickup_time is not None:
            package.mark_picked_up(occurred_at=pickup_time)
            changed = True
        elif package.status is not ItemStatus.IN_PROGRESS:
            # Reconciliation may repair stale/imported state backwards without
            # representing a new business lifecycle transition.
            package.status = ItemStatus.IN_PROGRESS
            reasons.append(PackageReconciliationReason.LIFECYCLE_STATE_INCONSISTENT)
            changed = True

        if package.current_location != current_location:
            package.current_location = current_location
            reasons.append(PackageReconciliationReason.ROUTE_PROGRESS_ADVANCED)
            changed = True

        return changed, reasons

    def _last_reached_city(
        self,
        route: DeliveryRoute,
        *,
        start: LocationCode,
        end: LocationCode,
        stop_times: dict[LocationCode, datetime],
        position_by_city: dict[LocationCode, int],
        now: datetime,
    ) -> LocationCode:
        """Find the latest package-route city reached by the given time.

        Args:
            route: Route containing the package path.
            start: Package pickup city.
            end: Package delivery city.
            stop_times: Known arrival times keyed by route city.
            position_by_city: Route indexes keyed by city.
            now: Business time used to determine reached stops.

        Returns:
            The last reached city between the package's pickup and delivery
            positions, defaulting to the pickup city.

        Raises:
            KeyError: If the package's start or end city is absent from the
                supplied route-position mapping.
        """
        last_city = start

        for index in range(position_by_city[start], position_by_city[end] + 1):
            city = route.locations[index]
            city_time = stop_times.get(city)

            if city_time is None or now < city_time:
                break

            last_city = city

        return last_city

    @staticmethod
    def _set_package_state(
        package: DeliveryPackage,
        *,
        status: ItemStatus,
        current_location: LocationCode,
    ) -> bool:
        """Set package status and location without recording lifecycle events.

        Args:
            package: Package requiring a direct state repair.
            status: Corrected package status.
            current_location: Corrected package location.

        Returns:
            Whether either field changed.
        """
        changed = False

        if package.status != status:
            package.status = status
            changed = True

        if package.current_location != current_location:
            package.current_location = current_location
            changed = True

        return changed

    @staticmethod
    def _restore_package_before_pickup(package: DeliveryPackage) -> bool:
        """Restore a package to its pre-pickup status and origin.

        Args:
            package: Package requiring a direct pre-pickup repair.

        Returns:
            Whether status or location changed.
        """
        changed = False

        if package.status is not ItemStatus.TODO:
            package.status = ItemStatus.TODO
            changed = True

        if package.current_location != package.start_location:
            package.current_location = package.start_location
            changed = True

        return changed
