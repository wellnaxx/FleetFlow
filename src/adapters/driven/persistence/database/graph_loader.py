"""Load a fully connected FleetFlow world graph from Postgres.

This loader is intentionally broad: it hydrates customers, packages, routes,
and trucks, then restores their in-memory bidirectional links.

Use this for full runtime/world hydration, not for every simple repository
get_by_id call.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.adapters.driven.persistence.database.executor import (
    RowDict,
    fetch_all_tx,
    transaction_cursor,
)
from src.adapters.driven.persistence.database.mappers import (
    map_customer,
    map_package,
    map_route,
    map_truck,
)
from src.adapters.driven.persistence.database.queries import QUERIES

if TYPE_CHECKING:
    from src.domain.entities.customer import Customer
    from src.domain.entities.delivery_package import DeliveryPackage
    from src.domain.entities.delivery_route import DeliveryRoute
    from src.domain.entities.truck import Truck


@dataclass(frozen=True)
class HydratedWorldGraph:
    """Fully connected domain graph loaded from Postgres."""

    customers: dict[int, Customer]
    packages: dict[int, DeliveryPackage]
    routes: dict[int, DeliveryRoute]
    trucks: dict[int, Truck]


def load_world_graph() -> HydratedWorldGraph:
    """Load and connect the full persisted world graph.

    Returns:
        Customers, packages, routes, and trucks keyed by their domain IDs.

    Raises:
        DatabaseError: If any SQL query fails.
        TypeError: If required DB columns have unexpected types.
        ValueError: If persisted FK relationships are inconsistent.
    """
    customer_rows, route_rows, package_rows, truck_rows = _load_world_rows()

    customers = _map_customers(customer_rows)
    routes, route_truck_ids = _map_routes(route_rows)
    trucks = _map_trucks(truck_rows)
    packages, package_route_ids = _map_packages(package_rows, customers)

    _link_trucks(routes, trucks, route_truck_ids)
    _link_packages(routes, packages, package_route_ids)

    return HydratedWorldGraph(
        customers=customers,
        packages=packages,
        routes=routes,
        trucks=trucks,
    )


def _load_world_rows() -> tuple[list[RowDict], list[RowDict], list[RowDict], list[RowDict]]:
    """Load all rows needed for full world hydration in one transaction."""
    with transaction_cursor() as cursor:
        customer_rows = fetch_all_tx(cursor, QUERIES.customers.list_all)
        route_rows = fetch_all_tx(cursor, QUERIES.routes.list_all)
        package_rows = fetch_all_tx(cursor, QUERIES.packages.list_all)
        truck_rows = fetch_all_tx(cursor, QUERIES.trucks.list_all)

    return customer_rows, route_rows, package_rows, truck_rows


def _map_customers(rows: list[RowDict]) -> dict[int, Customer]:
    customers: dict[int, Customer] = {}

    for row in rows:
        customer = map_customer(row)
        if customer.customer_id in customers:
            raise ValueError(f"Duplicate customer_id {customer.customer_id} in persisted data.")
        customers[customer.customer_id] = customer
        
    return customers


def _map_routes(rows: list[RowDict]) -> tuple[dict[int, DeliveryRoute], dict[int, int | None]]:
    rows_by_route_id: dict[int, list[RowDict]] = {}
    truck_ids_by_route_id: dict[int, int | None] = {}

    for row in rows:
        route_id = _int_value(row, "route_id")
        truck_vehicle_id = _optional_int_value(row, "truck_vehicle_id")

        rows_by_route_id.setdefault(route_id, []).append(row)

        if route_id in truck_ids_by_route_id and truck_ids_by_route_id[route_id] != truck_vehicle_id:
            raise ValueError(
                f"Route {route_id} has inconsistent truck_vehicle_id values: "
                f"{truck_ids_by_route_id[route_id]!r} and {truck_vehicle_id!r}."
            )

        truck_ids_by_route_id[route_id] = truck_vehicle_id

    routes = {
        route_id: map_route(sorted(route_rows, key=lambda item: _int_value(item, "stop_order")))
        for route_id, route_rows in rows_by_route_id.items()
    }

    return routes, truck_ids_by_route_id


def _map_trucks(rows: list[RowDict]) -> dict[int, Truck]:
    trucks: dict[int, Truck] = {}

    for row in rows:
        truck = map_truck(row)
        trucks[truck.vehicle_id] = truck

    return trucks


def _map_packages(
    rows: list[RowDict],
    customers: dict[int, Customer],
) -> tuple[dict[int, DeliveryPackage], dict[int, int | None]]:
    packages: dict[int, DeliveryPackage] = {}
    route_ids_by_package_id: dict[int, int | None] = {}

    for row in rows:
        package_id = _int_value(row, "package_id")
        customer_id = _int_value(row, "customer_id")
        route_id = _optional_int_value(row, "route_id")

        customer = customers.get(customer_id)
        if customer is None:
            raise ValueError(f"Package {package_id} references missing customer {customer_id}.")

        package = map_package(row, customer)
        customer.restore_package_link(package)

        packages[package_id] = package
        route_ids_by_package_id[package_id] = route_id

    return packages, route_ids_by_package_id


def _link_trucks(
    routes: dict[int, DeliveryRoute],
    trucks: dict[int, Truck],
    route_truck_ids: dict[int, int | None],
) -> None:
    for route_id, vehicle_id in route_truck_ids.items():
        if vehicle_id is None:
            continue

        route = routes[route_id]
        truck = trucks.get(vehicle_id)

        if truck is None:
            raise ValueError(f"Route {route_id} references missing truck {vehicle_id}.")

        route.truck = truck
        truck.route = route


def _link_packages(
    routes: dict[int, DeliveryRoute],
    packages: dict[int, DeliveryPackage],
    package_route_ids: dict[int, int | None],
) -> None:
    for package_id, route_id in package_route_ids.items():
        if route_id is None:
            continue

        route = routes.get(route_id)
        if route is None:
            raise ValueError(f"Package {package_id} references missing route {route_id}.")

        package = packages[package_id]
        route.restore_package_link(package, refresh_expected_arrival=False)


def _int_value(row: RowDict, column: str) -> int:
    value = row[column]

    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{column}: expected int, got {type(value).__name__}.")

    return value


def _optional_int_value(row: RowDict, column: str) -> int | None:
    value = row[column]

    if value is None:
        return None

    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{column}: expected int | None, got {type(value).__name__}.")

    return value
