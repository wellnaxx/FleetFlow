import contextlib
from datetime import datetime

from src.application.results.heartbeat_summary_result import HeartbeatSummary
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.entities.delivery_route import DeliveryRoute, RoutePosition
from src.domain.entities.truck import Truck
from src.domain.enums.item_status import ItemStatus
from src.ports.output.package_repository import PackageRepositoryPort
from src.ports.output.route_repository import RouteRepositoryPort
from src.ports.output.vehicle_manager import VehicleManagerPort


class HeartbeatService:
    def __init__(
        self,
        routes: RouteRepositoryPort,
        packages: PackageRepositoryPort,
        vehicles: VehicleManagerPort,
    ) -> None:
        self._routes = routes
        self._packages = packages
        self._vehicles = vehicles

    def advance(self, now: datetime | None = None) -> HeartbeatSummary:
        current_time = now or datetime.now()

        routes_updated = 0
        packages_updated = 0
        trucks_moved = 0
        trucks_released = 0

        for route in self._routes.list_all():
            new_status = self._compute_route_status(route, current_time)
            if getattr(route, "status", None) != new_status:
                route.status = new_status
                routes_updated += 1

            truck = route.truck
            position = route.current_position(current_time)

            if truck is not None:
                if position.kind == "UNSCHEDULED":
                    self._set_truck_unscheduled(truck)

                elif position.kind == "BEFORE_START":
                    if self._set_truck_before_start(truck, route):
                        trucks_moved += 1

                elif position.kind == "AT_STOP":
                    moved, released = self._set_truck_at_stop(truck, route, position, current_time)
                    if moved:
                        trucks_moved += 1
                    if released:
                        trucks_released += 1

                elif position.kind == "IN_TRANSIT":
                    if self._set_truck_in_transit(truck, route, position):
                        trucks_moved += 1

                elif position.kind == "AFTER_END":
                    if truck.release(now=current_time, force=False):
                        trucks_released += 1
                        trucks_moved += 1
                        route.truck = None

            packages_updated += self._update_packages_for_route(route, current_time)

        return HeartbeatSummary(
            routes_updated=routes_updated,
            packages_updated=packages_updated,
            trucks_moved=trucks_moved,
            trucks_released=trucks_released,
        )

    def _compute_route_status(self, route: DeliveryRoute, now: datetime) -> str:
        if route.departure_time is None:
            return "PLANNED"

        if route.eta_final is None:
            return "SCHEDULED"

        if now < route.departure_time:
            return "SCHEDULED"

        if now >= route.eta_final:
            return "COMPLETED"

        return "IN_PROGRESS"

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
        moved = truck.current_location != position.stop_city
        truck.current_location = position.stop_city
        truck.in_transit_to = None
        truck.route = route
        released = False
        if (
            position.stop_city == route.end_location
            and route.eta_final
            and now >= route.eta_final
            and truck.release(now=now, force=False)
        ):
            moved = True
            released = True
            route.truck = None
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

    def _update_packages_for_route(self, route: DeliveryRoute, now: datetime) -> int:
        changed = 0
        stop_times: dict[str, datetime] = {}

        if route.departure_time is not None:
            for city in route.locations:
                with contextlib.suppress(Exception):
                    stop_times[city] = route.arrival_time_at(city)

        pos_index = {city: index for index, city in enumerate(route.locations)}

        for package in route.packages:
            start = package.start_location
            end = package.end_location

            if route.departure_time is None:
                changed += self._set_package_state(package, status=ItemStatus.TODO, current_location=start)
                continue

            start_time = stop_times.get(start)
            end_time = stop_times.get(end)

            if start_time and now < start_time:
                changed += self._set_package_state(package, status=ItemStatus.TODO, current_location=start)
            elif end_time and now >= end_time:
                changed += self._set_package_state(package, status=ItemStatus.DONE, current_location=end)
            else:
                last_city = start
                if start_time:
                    for index in range(pos_index[start], pos_index[end] + 1):
                        city = route.locations[index]
                        city_time = stop_times.get(city)
                        if city_time and now >= city_time:
                            last_city = city
                        else:
                            break
                changed += self._set_package_state(
                    package,
                    status=ItemStatus.IN_PROGRESS,
                    current_location=last_city,
                )

            with contextlib.suppress(Exception):
                package.expected_arrival = route.arrival_time_at(end)

        return changed

    @staticmethod
    def _set_package_state(
        package: DeliveryPackage,
        *,
        status: ItemStatus,
        current_location: str,
    ) -> int:
        changed = 0
        if package.status != status:
            package.status = status
            changed += 1
        if package.current_location != current_location:
            package.current_location = current_location
            changed += 1
        return changed
