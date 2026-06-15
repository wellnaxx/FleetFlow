"""Runtime reconciliation of routes, packages, and truck state."""

import contextlib
from datetime import datetime

from src.application.results.heartbeat_summary_result import HeartbeatSummary
from src.application.results.truck_reconciliation_summary_result import TruckReconciliationSummary
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.entities.delivery_route import DeliveryRoute, RoutePosition, RoutePositionKind
from src.domain.entities.truck import Truck
from src.domain.enums.item_status import ItemStatus
from src.domain.enums.route_status import RouteStatus
from src.domain.enums.truck_release_reasons import TruckReleaseReason
from src.domain.value_objects.location_code import LocationCode


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
            Summary of entity-level changes made during reconciliation.
        """
        current_time = now or datetime.now()

        routes_updated: list[DeliveryRoute] = []
        packages_updated: list[DeliveryPackage] = []
        trucks_moved: list[Truck] = []
        trucks_released: list[Truck] = []

        for route in routes:
            new_status = self._compute_route_status(route, current_time)
            if route.status != new_status:
                self._apply_route_status(route, new_status)
                routes_updated.append(route)

            if update_trucks:
                truck_summary = self._reconcile_truck_for_route(route, current_time)
                trucks_moved.extend(truck_summary.trucks_moved)
                trucks_released.extend(truck_summary.trucks_released)

            package_changes = self._update_packages_for_route(route, current_time)
            packages_updated.extend(package_changes)

        return HeartbeatSummary(
            mutated_routes=tuple(routes_updated),
            mutated_packages=tuple(packages_updated),
            mutated_trucks_moved=tuple(trucks_moved),
            mutated_trucks_released=tuple(trucks_released),
        )

    def _reconcile_truck_for_route(
        self,
        route: DeliveryRoute,
        now: datetime,
    ) -> TruckReconciliationSummary:
        truck = route.truck
        if truck is None:
            return TruckReconciliationSummary()

        # current_position() reports the exact final ETA as AT_STOP, while times after
        # the final ETA are AFTER_END. Both paths can release the truck, but they cover
        # different position states.
        position = route.current_position(now)

        trucks_moved: list[Truck] = []
        trucks_released: list[Truck] = []

        if position.kind == RoutePositionKind.UNSCHEDULED:
            self._set_truck_unscheduled(truck)

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
            before_location = truck.current_location
            before_in_transit_to = truck.in_transit_to

            completion_time = self._validate_route_eta_final(route)

            if route.release_truck(
                now=now, force=False, reason=TruckReleaseReason.ROUTE_COMPLETED, occurred_at=completion_time
            ):
                trucks_released.append(truck)
                if truck.current_location != before_location or truck.in_transit_to != before_in_transit_to:
                    trucks_moved.append(truck)

        return TruckReconciliationSummary(
            trucks_moved=tuple(trucks_moved), trucks_released=tuple(trucks_released)
        )

    def _validate_route_eta_final(self, route: DeliveryRoute) -> datetime:
        completion_time = route.eta_final
        if completion_time is None:
            raise RuntimeError("Completed route has no completion time.")
        return completion_time

    def _compute_route_status(self, route: DeliveryRoute, now: datetime) -> RouteStatus:
        if route.departure_time is None:
            return RouteStatus.PLANNED

        if route.eta_final is None:
            return RouteStatus.SCHEDULED

        if now < route.departure_time:
            return RouteStatus.SCHEDULED

        if now >= route.eta_final:
            return RouteStatus.COMPLETED

        return RouteStatus.IN_PROGRESS

    def _apply_route_status(self, route: DeliveryRoute, new_status: RouteStatus) -> None:
        if new_status is RouteStatus.IN_PROGRESS:
            departure_time = route.departure_time
            if departure_time is None:
                raise RuntimeError("Started route has no departure time.")

            route.mark_started(occurred_at=departure_time)
            return

        if new_status is RouteStatus.COMPLETED:
            completion_time = route.eta_final
            if completion_time is None:
                raise RuntimeError("Completed route has no completion time.")

            route.mark_completed(occurred_at=completion_time)
            return

        route.status = new_status

    def _set_truck_unscheduled(self, truck: Truck) -> None:
        truck.in_transit_to = None

    def _set_truck_before_start(self, truck: Truck, route: DeliveryRoute) -> bool:
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
        moved = truck.current_location != position.stop_city or truck.in_transit_to is not None

        truck.current_location = position.stop_city
        truck.in_transit_to = None
        truck.route = route

        released = False

        if (
            position.stop_city == route.end_location
            and route.eta_final is not None
            and now >= route.eta_final
        ):
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
        moved = False
        if position.from_city and truck.current_location != position.from_city:
            truck.current_location = position.from_city
            moved = True
        if truck.in_transit_to != position.to_city:
            moved = True
        truck.in_transit_to = position.to_city
        truck.route = route
        return moved

    def _update_packages_for_route(self, route: DeliveryRoute, now: datetime) -> list[DeliveryPackage]:
        changed_packages: list[DeliveryPackage] = []
        stop_times: dict[LocationCode, datetime] = {}

        if route.departure_time is not None:
            for city in route.locations:
                with contextlib.suppress(ValueError):
                    stop_times[city] = route.arrival_time_at(city)

        pos_index = {city: index for index, city in enumerate(route.locations)}

        for package in route.packages:
            package_changed = False

            start = package.start_location
            end = package.end_location

            if route.departure_time is None:
                package_changed = self._restore_package_before_pickup(package)
                if package.expected_arrival is not None:
                    package.expected_arrival = None
                    package_changed = True

                if package_changed:
                    changed_packages.append(package)
                continue

            if start not in pos_index or end not in pos_index or pos_index[start] > pos_index[end]:
                package_changed = self._restore_package_before_pickup(package)
                if package.expected_arrival is not None:
                    package.expected_arrival = None
                    package_changed = True

                if package_changed:
                    changed_packages.append(package)
                continue

            start_time = stop_times.get(start)
            end_time = stop_times.get(end)

            if start_time and now < start_time:
                package_changed = self._restore_package_before_pickup(package)

            elif end_time and now >= end_time:
                package_changed = self._complete_package_lifecycle(
                    package,
                    pickup_time=start_time,
                    delivery_time=end_time,
                )
            else:
                package_changed = self._advance_package_in_progress(
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

            with contextlib.suppress(ValueError):
                expected_arrival = route.arrival_time_at(end)
                if package.expected_arrival != expected_arrival:
                    package.expected_arrival = expected_arrival
                    package_changed = True

            if package_changed:
                changed_packages.append(package)

        return changed_packages

    def _complete_package_lifecycle(
        self, package: DeliveryPackage, *, pickup_time: datetime | None, delivery_time: datetime
    ) -> bool:
        changed = False

        if package.status is ItemStatus.TODO:
            if pickup_time is None:
                # Missing schedule data prevents reconstructing the pickup event.
                # Repair the observed final state without inventing a timestamp.
                return self._set_package_state(
                    package,
                    status=ItemStatus.DONE,
                    current_location=package.end_location,
                )

            package.mark_picked_up(occurred_at=pickup_time)
            changed = True

        if package.status is ItemStatus.IN_PROGRESS:
            package.mark_delivered(occurred_at=delivery_time)
            changed = True

        if package.current_location != package.end_location:
            package.current_location = package.end_location
            changed = True

        return changed

    def _advance_package_in_progress(
        self,
        package: DeliveryPackage,
        *,
        pickup_time: datetime | None,
        current_location: LocationCode,
    ) -> bool:
        changed = False

        if package.status is ItemStatus.TODO and pickup_time is not None:
            package.mark_picked_up(occurred_at=pickup_time)
            changed = True
        elif package.status is not ItemStatus.IN_PROGRESS:
            # Reconciliation may repair stale/imported state backwards without
            # representing a new business lifecycle transition.
            package.status = ItemStatus.IN_PROGRESS
            changed = True

        if package.current_location != current_location:
            package.current_location = current_location
            changed = True

        return changed

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
        changed = False

        if package.status is not ItemStatus.TODO:
            package.status = ItemStatus.TODO
            changed = True

        if package.current_location != package.start_location:
            package.current_location = package.start_location
            changed = True

        return changed
