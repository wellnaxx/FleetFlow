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
from src.adapters.driven.persistence.database.mappers import as_package_row, map_package_with_customer
from src.adapters.driven.persistence.database.queries import QUERIES
from src.domain.entities.customer import Customer
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.entities.delivery_route import DeliveryRoute


@dataclass(frozen=True)
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
        package_rows = fetch_all_tx(cursor, QUERIES.packages.list_unassigned)

        return [_hydrate_unassigned_package_graph(row) for row in package_rows]


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
        Hydrated package graph for one assigned package.

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
