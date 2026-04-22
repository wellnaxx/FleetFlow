from typing import Any

from src.application.dto.world_state_snapshot_dto import (
    CountersSnapshot,
    CustomerSnapshot,
    PackageSnapshot,
    RouteSnapshot,
    WorldSnapshotData,
    WorldStateSnapshot,
)
from src.core.application_data import ApplicationData
from src.ports.output.world_state_gateway import WorldStateGatewayPort


class ApplicationDataWorldStateGateway(WorldStateGatewayPort):
    def __init__(self, app_data: ApplicationData) -> None:
        self._app_data = app_data

    def build_snapshot(self) -> WorldStateSnapshot:
        raw = self._app_data._dump_state()  # pyright: ignore[reportPrivateUsage]
        return self._snapshot_from_raw(raw)

    def apply_snapshot(self, snapshot: WorldStateSnapshot) -> None:
        raw = self._raw_from_snapshot(snapshot)
        self._app_data._apply_state(raw)  # pyright: ignore[reportPrivateUsage]

    def _snapshot_from_raw(self, raw: dict[str, Any]) -> WorldStateSnapshot:
        counters = raw.get("counters", {})
        customers = [
            CustomerSnapshot(
                customer_id=int(customer["customer_id"]),
                name=str(customer["name"]),
                email=str(customer.get("email", "")),
                phone=str(customer.get("phone", "")),
            )
            for customer in raw.get("customers", [])
        ]
        packages = [
            PackageSnapshot(
                package_id=int(package["package_id"]),
                start=str(package["start"]),
                end=str(package["end"]),
                weight=float(package["weight"]),
                customer_id=int(package["customer_id"]),
                route_id=int(package["route_id"]) if package.get("route_id") is not None else None,
            )
            for package in raw.get("packages", [])
        ]
        routes = [
            RouteSnapshot(
                route_id=int(route["route_id"]),
                locations=[str(location) for location in route["locations"]],
                departure_time=route.get("departure_time"),
                truck_vehicle_id=int(route["truck_vehicle_id"])
                if route.get("truck_vehicle_id") is not None
                else None,
                package_ids=[int(package_id) for package_id in route.get("package_ids", [])],
            )
            for route in raw.get("routes", [])
        ]

        return WorldStateSnapshot(
            schema_version=int(raw.get("schema_version", 1)),
            world=WorldSnapshotData(
                counters=CountersSnapshot(
                    next_customer_id=int(counters.get("next_customer_id", 1)),
                    next_package_id=int(counters.get("next_package_id", 1)),
                    next_route_id=int(counters.get("next_route_id", 1)),
                ),
                customers=customers,
                packages=packages,
                routes=routes,
            ),
            users=raw.get("users"),
        )

    def _raw_from_snapshot(self, snapshot: WorldStateSnapshot) -> dict[str, Any]:
        return {
            "schema_version": snapshot.schema_version,
            "counters": {
                "next_customer_id": snapshot.world.counters.next_customer_id,
                "next_package_id": snapshot.world.counters.next_package_id,
                "next_route_id": snapshot.world.counters.next_route_id,
            },
            "customers": [
                {
                    "customer_id": customer.customer_id,
                    "name": customer.name,
                    "email": customer.email,
                    "phone": customer.phone,
                }
                for customer in snapshot.world.customers
            ],
            "packages": [
                {
                    "package_id": package.package_id,
                    "start": package.start,
                    "end": package.end,
                    "weight": package.weight,
                    "customer_id": package.customer_id,
                    "route_id": package.route_id,
                }
                for package in snapshot.world.packages
            ],
            "routes": [
                {
                    "route_id": route.route_id,
                    "locations": list(route.locations),
                    "departure_time": route.departure_time,
                    "truck_vehicle_id": route.truck_vehicle_id,
                    "package_ids": list(route.package_ids),
                }
                for route in snapshot.world.routes
            ],
            "users": snapshot.users,
        }
