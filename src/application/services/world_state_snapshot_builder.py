from collections.abc import Callable, Iterable
from typing import Any

from src.adapters.driven.persistence.json.serialization import dt_to_str
from src.application.dto.world_state_snapshot_dto import (
    CountersSnapshot,
    CustomerSnapshot,
    PackageSnapshot,
    RouteSnapshot,
    TruckSnapshot,
    WorldSnapshotData,
    WorldStateSnapshot,
)
from src.domain.entities.customer import Customer
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.entities.truck import Truck


class WorldStateSnapshotBuilder:
    """Service to build world-state snapshots from live runtime state."""

    def build_world_state_snapshot(
        self,
        *,
        customers: Iterable[Customer],
        packages: Iterable[DeliveryPackage],
        routes: Iterable[DeliveryRoute],
        trucks: Iterable[Truck],
        counters: CountersSnapshot,
        schema_version: int,
    ) -> WorldStateSnapshot:
        """Build a world-state snapshot from live runtime state.

        Args:
            customers: Live customer objects.
            packages: Live package objects.
            routes: Live route objects.
            trucks: Live truck objects.
            counters: Repository id counters.
            schema_version: The version of the schema to use for the snapshot.
        Returns:
            WorldStateSnapshot DTO representing the current runtime state.
        """
        customer_snapshots = _build_customer_snapshots(customers)
        package_snapshots = _build_package_snapshots(packages)
        route_snapshots = _build_route_snapshots(routes)
        truck_snapshots = _build_truck_snapshots(trucks)

        world = WorldSnapshotData(
            counters=counters,
            customers=customer_snapshots,
            packages=package_snapshots,
            routes=route_snapshots,
            trucks=truck_snapshots,
        )
        return WorldStateSnapshot(schema_version=schema_version, world=world)


def _sorted_snapshots[T, S](
    items: Iterable[T], *, key: Callable[[T], Any], transform: Callable[[T], S]
) -> tuple[S, ...]:
    return tuple(transform(item) for item in sorted(items, key=key))


def _build_customer_snapshots(customers: Iterable[Customer]) -> tuple[CustomerSnapshot, ...]:
    return _sorted_snapshots(
        customers,
        key=lambda customer: customer.customer_id,
        transform=lambda customer: CustomerSnapshot(
            customer_id=customer.customer_id,
            name=customer.name,
            email=customer.email or "",
            phone=customer.phone_number or "",
        ),
    )


def _build_package_snapshots(packages: Iterable[DeliveryPackage]) -> tuple[PackageSnapshot, ...]:
    return _sorted_snapshots(
        packages,
        key=lambda package: package.package_id,
        transform=lambda package: PackageSnapshot(
            package_id=package.package_id,
            start=package.start_location,
            end=package.end_location,
            weight=package.weight,
            customer_id=package.customer.customer_id,
            route_id=package.route.route_id if package.route is not None else None,
        ),
    )


def _build_route_snapshots(routes: Iterable[DeliveryRoute]) -> tuple[RouteSnapshot, ...]:
    return _sorted_snapshots(
        routes,
        key=lambda route: route.route_id,
        transform=lambda route: RouteSnapshot(
            route_id=route.route_id,
            locations=tuple(route.locations),
            departure_time=dt_to_str(route.departure_time),
            truck_vehicle_id=route.truck.vehicle_id if route.truck is not None else None,
            package_ids=tuple(sorted(package.package_id for package in route.packages)),
        ),
    )


def _build_truck_snapshots(trucks: Iterable[Truck]) -> tuple[TruckSnapshot, ...]:
    return _sorted_snapshots(
        trucks,
        key=lambda truck: truck.vehicle_id,
        transform=lambda truck: TruckSnapshot(
            vehicle_id=truck.vehicle_id,
            status=truck.status,
            current_location=truck.current_location,
            route_id=truck.route.route_id if truck.route is not None else None,
            busy_from=dt_to_str(truck.busy_from),
            busy_until=dt_to_str(truck.busy_until),
            in_transit_to=truck.in_transit_to,
        ),
    )
