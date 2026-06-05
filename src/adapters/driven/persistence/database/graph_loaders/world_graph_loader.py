"""Load a fully connected FleetFlow world graph from Postgres.

This loader is intentionally broad: it hydrates customers, packages, routes,
and trucks, then restores their in-memory bidirectional links.

Use this for full runtime/world hydration, not for every simple repository
get_by_id call.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING

from src.adapters.driven.persistence.database.executor import (
    RowDict,
    fetch_all_tx,
    transaction_cursor,
)
from src.adapters.driven.persistence.database.graph_loaders.shared import (
    link_packages_to_routes,
    link_route_trucks,
    map_customers,
    map_packages_with_existing_customers,
    map_routes,
    map_trucks,
)
from src.adapters.driven.persistence.database.queries import QUERIES

if TYPE_CHECKING:
    from collections.abc import Mapping

    from src.domain.entities.customer import Customer
    from src.domain.entities.delivery_package import DeliveryPackage
    from src.domain.entities.delivery_route import DeliveryRoute
    from src.domain.entities.truck import Truck


@dataclass(frozen=True, slots=True)
class HydratedWorldGraph:
    """Fully connected domain graph loaded from Postgres.

    Args:
        customers: Customers keyed by customer id.
        packages: Packages keyed by package id.
        routes: Routes keyed by route id.
        trucks: Trucks keyed by vehicle id.
    """

    customers: Mapping[int, Customer]
    packages: Mapping[int, DeliveryPackage]
    routes: Mapping[int, DeliveryRoute]
    trucks: Mapping[int, Truck]


def load_world_graph() -> HydratedWorldGraph:
    """Load and connect the full persisted world graph.

    Returns:
        Customers, packages, routes, and trucks keyed by their domain IDs.

    Raises:
        DatabaseError: If any SQL query fails.
        KeyError: If a required database column is missing.
        TypeError: If required database columns have unexpected types.
        ValueError: If persisted relationships are inconsistent.
    """
    customer_rows, route_rows, package_rows, truck_rows = _load_world_rows()

    customers = map_customers(customer_rows)
    routes, route_truck_ids = map_routes(route_rows)
    trucks = map_trucks(truck_rows)
    packages, package_route_ids = map_packages_with_existing_customers(package_rows, customers)

    link_route_trucks(routes, trucks, route_truck_ids)
    link_packages_to_routes(routes, packages, package_route_ids)

    return HydratedWorldGraph(
        customers=MappingProxyType(customers),
        packages=MappingProxyType(packages),
        routes=MappingProxyType(routes),
        trucks=MappingProxyType(trucks),
    )


def _load_world_rows() -> tuple[list[RowDict], list[RowDict], list[RowDict], list[RowDict]]:
    """Load all rows needed for full world hydration in one transaction.

    Returns:
        Customer rows, route/stop rows, package rows, and truck rows.

    Raises:
        DatabaseError: If any SQL query fails.
    """
    with transaction_cursor() as cursor:
        customer_rows = fetch_all_tx(cursor, QUERIES.customers.list_all)
        route_rows = fetch_all_tx(cursor, QUERIES.routes.list_all)
        package_rows = fetch_all_tx(cursor, QUERIES.packages.list_all)
        truck_rows = fetch_all_tx(cursor, QUERIES.trucks.list_all)

    return customer_rows, route_rows, package_rows, truck_rows
