from dataclasses import dataclass


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
    locations: tuple[str, ...]
    departure_time: str | None
    truck_vehicle_id: int | None
    package_ids: tuple[int, ...]


@dataclass(frozen=True)
class TruckSnapshot:
    vehicle_id: int
    status: str
    current_location: str | None
    route_id: int | None
    busy_from: str | None
    busy_until: str | None
    in_transit_to: str | None


@dataclass(frozen=True)
class WorldSnapshotData:
    counters: CountersSnapshot
    customers: tuple[CustomerSnapshot, ...]
    packages: tuple[PackageSnapshot, ...]
    routes: tuple[RouteSnapshot, ...]
    trucks: tuple[TruckSnapshot, ...] = ()


@dataclass(frozen=True)
class WorldStateSnapshot:
    schema_version: int
    world: WorldSnapshotData
    users: None = None
