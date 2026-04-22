from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CountersSnapshot:
    next_customer_id: int
    next_package_id: int
    next_route_id: int


@dataclass(frozen=True)
class CustomerSnapshot:
    customer_id: int
    name: str
    email: str
    phone: str


@dataclass(frozen=True)
class PackageSnapshot:
    package_id: int
    start: str
    end: str
    weight: float
    customer_id: int
    route_id: int | None


@dataclass(frozen=True)
class RouteSnapshot:
    route_id: int
    locations: list[str]
    departure_time: str | None
    truck_vehicle_id: int | None
    package_ids: list[int]


@dataclass(frozen=True)
class WorldSnapshotData:
    counters: CountersSnapshot
    customers: list[CustomerSnapshot]
    packages: list[PackageSnapshot]
    routes: list[RouteSnapshot]


@dataclass(frozen=True)
class WorldStateSnapshot:
    schema_version: int
    world: WorldSnapshotData
    users: Any | None = None
