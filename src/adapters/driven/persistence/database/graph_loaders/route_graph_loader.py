"""Load route aggregate graphs from Postgres.

This module hydrates route-centered graphs only.

It deliberately does not load:
- unassigned packages
- free trucks
- customers unrelated to route packages

Use `load_route_graph(route_id)` for one route aggregate.
Use `load_route_graphs()` for all persisted route aggregates.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING

from src.adapters.driven.persistence.database.executor import (
    RowDict,
    fetch_all_tx,
    fetch_one_tx,
    transaction_cursor,
)
from src.adapters.driven.persistence.database.graph_loaders.shared import (
    link_packages_to_routes,
    link_route_packages,
    link_route_truck,
    link_route_trucks,
    map_joined_package_rows,
    map_routes,
    map_trucks,
    route_stop_order,
    validate_same_customer,
)
from src.adapters.driven.persistence.database.mappers.route import map_route
from src.adapters.driven.persistence.database.mappers.truck import map_truck
from src.adapters.driven.persistence.database.queries import QUERIES

if TYPE_CHECKING:
    from collections.abc import Mapping

    from psycopg import Cursor

    from src.adapters.driven.persistence.database.executor import Row
    from src.domain.entities.customer import Customer
    from src.domain.entities.delivery_package import DeliveryPackage
    from src.domain.entities.delivery_route import DeliveryRoute
    from src.domain.entities.truck import Truck


@dataclass(frozen=True)
class HydratedRouteGraph:
    """Connected domain graph for one route aggregate.

    Args:
        route: Hydrated route with package and truck links restored.
        truck: Assigned truck, or `None` when the route has no truck.
        packages: Route packages keyed by package id.
        customers: Customers for the route packages keyed by customer id.
    """

    route: DeliveryRoute
    truck: Truck | None
    packages: Mapping[int, DeliveryPackage]
    customers: Mapping[int, Customer]


def load_route_graph(route_id: int) -> HydratedRouteGraph | None:
    """Load one route and its connected truck, packages, and customers.

    Args:
        route_id: Route id to load.

    Returns:
        Hydrated route graph, or `None` when the route does not exist.

    Raises:
        DatabaseError: If any SQL query fails.
        KeyError: If a required database column is missing.
        TypeError: If required database columns have unexpected types.
        ValueError: If persisted route relationships are inconsistent.
    """
    with transaction_cursor() as cursor:
        return load_route_graph_tx(cursor, route_id)


def load_route_graph_tx(cursor: Cursor[Row], route_id: int) -> HydratedRouteGraph | None:
    """Load one route graph inside an existing transaction.

    Args:
        cursor: Cursor owned by the caller's active transaction.
        route_id: Route id to load.

    Returns:
        Hydrated route graph, or `None` when the route does not exist.

    Raises:
        DatabaseError: If any SQL query fails.
        KeyError: If a required database column is missing.
        TypeError: If required database columns have unexpected types.
        ValueError: If persisted route relationships are inconsistent.
    """
    route_rows, truck_row, package_rows = _load_route_rows_tx(cursor, route_id)
    return hydrate_route_graph_from_rows(route_rows, truck_row, package_rows)


def hydrate_route_graph_from_rows(
    route_rows: list[RowDict],
    truck_row: RowDict | None,
    package_rows: list[RowDict],
) -> HydratedRouteGraph | None:
    """Hydrate a route graph from already-loaded database rows.

    Args:
        route_rows: Route/stop rows for one route.
        truck_row: Assigned truck row, or `None`.
        package_rows: Joined package/customer rows for the route.

    Returns:
        Hydrated route graph, or `None` when route rows are empty.

    Raises:
        KeyError: If a required database column is missing.
        TypeError: If required database columns have unexpected types.
        ValueError: If persisted route relationships are inconsistent.
    """

    if not route_rows:
        return None

    route = map_route(sorted(route_rows, key=route_stop_order))
    truck = map_truck(truck_row) if truck_row is not None else None
    packages, customers, _package_route_ids = map_joined_package_rows(
        package_rows,
        expected_route_id=route.route_id,
    )

    link_route_truck(route, truck)
    link_route_packages(route, packages)

    return HydratedRouteGraph(
        route=route,
        truck=truck,
        packages=MappingProxyType(packages),
        customers=MappingProxyType(customers),
    )


def load_route_graphs() -> list[HydratedRouteGraph]:
    """Load all route aggregates and their connected assigned objects.

    This loads all routes, assigned trucks, assigned packages, and customers
    for those assigned packages. It does not load free trucks, unassigned
    packages, or unrelated customers.

    Returns:
        Hydrated route graphs ordered by route id.

    Raises:
        DatabaseError: If any SQL query fails.
        KeyError: If a required database column is missing.
        TypeError: If required database columns have unexpected types.
        ValueError: If persisted route relationships are inconsistent.
    """
    with transaction_cursor() as cursor:
        route_rows = fetch_all_tx(cursor, QUERIES.routes.list_all)
        return _hydrate_route_graphs_from_rows_tx(cursor, route_rows)


def load_route_graph_page(limit: int, offset: int) -> list[HydratedRouteGraph]:
    """Load a page of route aggregates and their connected assigned objects.
    
    Args:
        limit: Maximum number of routes to return.
        offset: Number of routes to skip.

    Returns:
        Hydrated route graphs for the requested page, ordered by route id.

    Raises:
        DatabaseError: If any SQL query fails.
        KeyError: If a required database column is missing.
        TypeError: If required database columns have unexpected types.
        ValueError: If persisted route relationships are inconsistent.
    """
    with transaction_cursor() as cursor:
        route_rows = fetch_all_tx(cursor, QUERIES.routes.list_page, (limit, offset))
        return _hydrate_route_graphs_from_rows_tx(cursor, route_rows)


def load_route_graph_page_with_total(limit: int, offset: int) -> tuple[list[HydratedRouteGraph], int]:
    """Load a route page and total count from one route-page query.
    
    Args:
        limit: Maximum number of routes to return.
        offset: Number of routes to skip.

    Returns:
        Tuple of (hydrated route graphs for the page, total count of all routes).

    Raises:
        DatabaseError: If any SQL query fails.
        KeyError: If a required database column is missing.
        TypeError: If required database columns have unexpected types or total is not an integer.
        ValueError: If persisted route relationships are inconsistent.
    """
    with transaction_cursor() as cursor:
        rows = fetch_all_tx(cursor, QUERIES.routes.list_page_with_total, (limit, offset))
        route_rows, total = _split_route_page_rows_and_total(rows)
        return _hydrate_route_graphs_from_rows_tx(cursor, route_rows), total


def _hydrate_route_graphs_from_rows_tx(
    cursor: Cursor[Row],
    route_rows: list[RowDict],
) -> list[HydratedRouteGraph]:
    """Hydrate route graphs from already-loaded route/stop rows."""
    routes, route_truck_ids = map_routes(route_rows)
    route_ids = sorted(routes)
    if not route_ids:
        return []

    truck_rows = fetch_all_tx(cursor, QUERIES.trucks.list_assigned_by_routes, (route_ids,))
    package_rows = fetch_all_tx(cursor, QUERIES.packages.list_assigned_by_routes, (route_ids,))

    trucks = map_trucks(truck_rows)
    packages, _customers, package_route_ids = map_joined_package_rows(package_rows)

    link_route_trucks(routes, trucks, route_truck_ids)
    link_packages_to_routes(routes, packages, package_route_ids)

    return [_build_route_graph(route) for route in sorted(routes.values(), key=lambda route: route.route_id)]


def _split_route_page_rows_and_total(rows: list[RowDict]) -> tuple[list[RowDict], int]:
    """Extract route rows and a validated total from page-with-total rows."""
    if not rows:
        return [], 0

    total = rows[0]["total"]
    if not isinstance(total, int) or isinstance(total, bool):
        raise TypeError("Route count must be an integer.")

    return [row for row in rows if row["route_id"] is not None], total


def _load_route_rows_tx(
    cursor: Cursor[Row],
    route_id: int,
) -> tuple[list[RowDict], RowDict | None, list[RowDict]]:
    """Load rows needed to hydrate one route graph.

    Args:
        cursor: Cursor owned by an active transaction.
        route_id: Route id to load.

    Returns:
        Route rows, assigned truck row if present, and joined package/customer rows.

    Raises:
        DatabaseError: If any SQL query fails.
    """
    route_rows = fetch_all_tx(cursor, QUERIES.routes.get_by_id, (route_id,))
    truck_row = fetch_one_tx(cursor, QUERIES.trucks.get_by_route_id, (route_id,))
    package_rows = fetch_all_tx(cursor, QUERIES.packages.list_by_route, (route_id,))

    return route_rows, truck_row, package_rows


def _build_route_graph(route: DeliveryRoute) -> HydratedRouteGraph:
    """Build a route graph from an already linked route object.

    Args:
        route: Route with package and truck links already restored.

    Returns:
        Hydrated route graph containing only this route's connected objects.

    Raises:
        ValueError: If package/customer links are inconsistent.
    """
    route_packages = {
        package.package_id: package
        for package in sorted(route.packages, key=lambda package: package.package_id)
    }

    route_customers: dict[int, Customer] = {}

    for package in route_packages.values():
        customer = package.customer
        existing_customer = route_customers.get(customer.customer_id)

        if existing_customer is not None and existing_customer is not customer:
            validate_same_customer(existing_customer, customer)

        route_customers[customer.customer_id] = customer

    return HydratedRouteGraph(
        route=route,
        truck=route.truck,
        packages=MappingProxyType(route_packages),
        customers=MappingProxyType(route_customers),
    )
