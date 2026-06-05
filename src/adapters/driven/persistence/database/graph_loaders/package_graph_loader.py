from dataclasses import dataclass

from psycopg import Cursor

from src.adapters.driven.persistence.database.executor import (
    Row,
    RowDict,
    fetch_all_tx,
    fetch_one_tx,
    transaction_cursor,
)
from src.adapters.driven.persistence.database.graph_loaders.route_graph_loader import (
    HydratedRouteGraph,
    load_route_graph_tx,
)
from src.adapters.driven.persistence.database.mappers.package import as_package_row, map_package_with_customer
from src.adapters.driven.persistence.database.queries import QUERIES
from src.domain.entities.customer import Customer
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.enums.item_status import ItemStatus


@dataclass(frozen=True, slots=True)
class HydratedPackageGraph:
    """Connected domain graph for one package aggregate.

    Args:
        package: Hydrated package with customer link restored.
        customer: Customer for the package.
        route: Assigned route, or `None` when the package is not assigned to a route.
    """

    package: DeliveryPackage
    customer: Customer
    route: DeliveryRoute | None = None


def load_package_graph(package_id: int) -> HydratedPackageGraph | None:
    """Load one package and its connected customer and route.

    Args:
        package_id: Package id to load.

    Returns:
        Hydrated package graph, or `None` when the package does not exist.

    Raises:
        ValueError: When the package is assigned to a route, but the route does not exist.
        DatabaseError: If any SQL query fails.
        KeyError: If a required database column is missing.
        TypeError: If required database columns have unexpected types.
    """
    with transaction_cursor() as cursor:
        package_row = fetch_one_tx(cursor, QUERIES.packages.get_by_id_with_customer, (package_id,))
        if package_row is None:
            return None

        return _hydrate_package_graph_tx(cursor, package_row, {})


def load_package_graphs() -> list[HydratedPackageGraph]:
    """Load all packages and their connected customers and routes.

    Returns:
        List of hydrated package graphs for all persisted packages.

    Raises:
        ValueError: When a package is assigned to a route, but the route does not exist.
        DatabaseError: If any SQL query fails.
        KeyError: If a required database column is missing.
        TypeError: If required database columns have unexpected types.
    """
    with transaction_cursor() as cursor:
        package_rows = fetch_all_tx(cursor, QUERIES.packages.list_all_with_customers)

        route_graphs: dict[int, HydratedRouteGraph] = {}
        package_graphs: list[HydratedPackageGraph] = [
            _hydrate_package_graph_tx(cursor, package_row, route_graphs) for package_row in package_rows
        ]

        return sorted(package_graphs, key=lambda graph: graph.package.package_id)


def load_package_graph_page(limit: int, offset: int) -> list[HydratedPackageGraph]:
    """Load a page of packages and their connected customers and routes.

    Args:
        limit: Maximum number of packages to load.
        offset: Number of packages to skip.

    Returns:
        List of hydrated package graphs in the requested page.

    Raises:
        ValueError: When a package is assigned to a route, but the route does not exist.
        DatabaseError: If any SQL query fails.
        KeyError: If a required database column is missing.
        TypeError: If required database columns have unexpected types.
    """
    with transaction_cursor() as cursor:
        package_rows = fetch_all_tx(cursor, QUERIES.packages.list_page_with_customers, (limit, offset))

        route_graphs: dict[int, HydratedRouteGraph] = {}
        package_graphs: list[HydratedPackageGraph] = [
            _hydrate_package_graph_tx(cursor, package_row, route_graphs) for package_row in package_rows
        ]

        return sorted(package_graphs, key=lambda graph: graph.package.package_id)


def load_package_graph_page_with_total(limit: int, offset: int) -> tuple[list[HydratedPackageGraph], int]:
    """Load a package page with the total count from one database query."""
    with transaction_cursor() as cursor:
        rows = fetch_all_tx(cursor, QUERIES.packages.list_page_with_total, (limit, offset))
        package_rows, total = _split_page_rows_and_total(rows, "Package total")

        route_graphs: dict[int, HydratedRouteGraph] = {}
        package_graphs = [
            _hydrate_package_graph_tx(cursor, package_row, route_graphs) for package_row in package_rows
        ]

        return sorted(package_graphs, key=lambda graph: graph.package.package_id), total


def load_unassigned_package_graphs() -> list[HydratedPackageGraph]:
    """Load all unassigned packages and their connected customers.

    Returns:
        List of hydrated package graphs for all persisted unassigned packages.

    Raises:
        DatabaseError: If any SQL query fails.
        KeyError: If a required database column is missing.
        TypeError: If required database columns have unexpected types.
    """
    with transaction_cursor() as cursor:
        package_rows = fetch_all_tx(cursor, QUERIES.packages.list_unassigned, (ItemStatus.TODO.value,))

        return [_hydrate_unassigned_package_graph(row) for row in package_rows]


def load_unassigned_package_graph_page(limit: int, offset: int) -> list[HydratedPackageGraph]:
    """Load a page of unassigned packages and their connected customers.

    Args:
        limit: Maximum number of packages to load.
        offset: Number of packages to skip.

    Returns:
        List of hydrated unassigned package graphs in the requested page.

    Raises:
        DatabaseError: If any SQL query fails.
        KeyError: If a required database column is missing.
        TypeError: If required database columns have unexpected types.
    """
    with transaction_cursor() as cursor:
        package_rows = fetch_all_tx(
            cursor,
            QUERIES.packages.list_unassigned_page,
            (ItemStatus.TODO.value, limit, offset),
        )

        return [_hydrate_unassigned_package_graph(row) for row in package_rows]


def load_unassigned_package_graph_page_with_total(
    limit: int, offset: int
) -> tuple[list[HydratedPackageGraph], int]:
    """Load an unassigned package page and total from one database query."""
    with transaction_cursor() as cursor:
        rows = fetch_all_tx(
            cursor,
            QUERIES.packages.list_unassigned_page_with_total,
            (ItemStatus.TODO.value, limit, offset, ItemStatus.TODO.value),
        )
        package_rows, total = _split_page_rows_and_total(rows, "Unassigned package total")
        return [_hydrate_unassigned_package_graph(row) for row in package_rows], total


def _split_page_rows_and_total(rows: list[RowDict], label: str) -> tuple[list[RowDict], int]:
    """Extract package rows and a validated total from page-with-total rows."""
    if not rows:
        return [], 0

    total = rows[0]["total"]
    if not isinstance(total, int) or isinstance(total, bool):
        raise TypeError(f"{label} must be an integer.")

    return [row for row in rows if row["package_id"] is not None], total


def _hydrate_package_graph_tx(
    cursor: Cursor[Row],
    package_row: RowDict,
    route_graphs: dict[int, HydratedRouteGraph],
) -> HydratedPackageGraph:
    """Hydrate one assigned package graph from a package row.

    Args:
        cursor: Cursor owned by an active transaction.
        package_row: Package row with joined customer columns.
        route_graphs: Cache of already hydrated route graphs keyed by route id.

    Returns:
        Hydrated package graph for one package.

    Raises:
        ValueError: When the package is assigned to a route, but the route does not exist.
        KeyError: If a required database column is missing.
        TypeError: If required database columns have unexpected types.
    """
    typed = as_package_row(package_row)
    route_id = typed["route_id"]

    if route_id is None:
        return _hydrate_unassigned_package_graph(package_row)

    route_graph = route_graphs.get(route_id)
    if route_graph is None:
        route_graph = load_route_graph_tx(cursor, route_id)
        if route_graph is None:
            raise ValueError(f"Package {typed['package_id']} references missing route {route_id}.")
        route_graphs[route_id] = route_graph

    package = route_graph.packages.get(typed["package_id"])
    if package is None:
        raise ValueError(
            f"Package {typed['package_id']} has route_id={route_id} in the database "
            f"but was not found in route {route_id}'s package list. "
            "This indicates inconsistent package-route hydration."
        )

    return HydratedPackageGraph(package=package, customer=package.customer, route=route_graph.route)


def _hydrate_unassigned_package_graph(package_row: RowDict) -> HydratedPackageGraph:
    """Hydrate one unassigned package graph from a package row.

    Args:
        package_row: Package row with joined customer columns.

    Returns:
        Hydrated package graph for one unassigned package.

    Raises:
        KeyError: If a required database column is missing.
        TypeError: If required database columns have unexpected types.
    """
    package = map_package_with_customer(package_row)
    return HydratedPackageGraph(package=package, customer=package.customer, route=None)
