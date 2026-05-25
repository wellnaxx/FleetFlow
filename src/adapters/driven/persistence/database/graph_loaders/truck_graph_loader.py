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
from src.adapters.driven.persistence.database.mappers.truck import map_truck
from src.adapters.driven.persistence.database.queries import QUERIES
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.entities.truck import Truck


@dataclass(frozen=True)
class HydratedTruckGraph:
    """Connected domain graph for one truck aggregate.

    Args:
        truck: Truck with route link restored.
        route: Assigned route, or `None` when the truck has no route.
    """

    truck: Truck
    route: DeliveryRoute | None = None


def load_truck_graph(vehicle_id: int) -> HydratedTruckGraph | None:
    """Load a truck and its connected route.

    Args:
        vehicle_id: ID of the truck to load.

    Returns:
        Hydrated truck graph, or `None` when the truck does not exist.

    Raises:
            DatabaseError: If the select operation fails.
            KeyError: If a required truck or route column is missing.
            TypeError: If a required truck or route column has an unexpected type.
            ValueError: If persisted truck or route data is invalid or inconsistent.
    """
    with transaction_cursor() as cursor:
        truck_row = fetch_one_tx(cursor, QUERIES.trucks.get_by_id_with_route, (vehicle_id,))
        if truck_row is None:
            return None

        return _hydrate_truck_graph_tx(cursor, truck_row, {})


def load_truck_graphs() -> list[HydratedTruckGraph]:
    """Load all trucks and their connected routes.

    Returns:
        List of hydrated truck graphs for all persisted trucks.

    Raises:
        DatabaseError: If the select operation fails.
        KeyError: If a required truck or route column is missing.
        TypeError: If a required truck or route column has an unexpected type.
        ValueError: If persisted truck or route data is invalid or inconsistent.
    """
    with transaction_cursor() as cursor:
        truck_rows = fetch_all_tx(cursor, QUERIES.trucks.list_all_with_route)

        route_graphs: dict[int, HydratedRouteGraph] = {}
        truck_graphs: list[HydratedTruckGraph] = [
            _hydrate_truck_graph_tx(cursor, truck_row, route_graphs) for truck_row in truck_rows
        ]

        return sorted(truck_graphs, key=lambda graph: graph.truck.vehicle_id)


def _hydrate_truck_graph_tx(
    cursor: Cursor[Row],
    truck_row: RowDict,
    route_graphs: dict[int, HydratedRouteGraph],
) -> HydratedTruckGraph:
    """Hydrate one truck graph from a truck row and route graph cache.
    Args:
        cursor: Cursor owned by an active transaction.
        truck_row: Truck row to hydrate from.
        route_graphs: Cache of already hydrated route graphs to link to.

    Returns:
        Hydrated truck graph.

    Raises:
        ValueError: If the truck row references a route id that does not exist, or if the
            truck-row-to-route-graph linkage is inconsistent.
        KeyError: If a required truck or route column is missing.
        TypeError: If a required truck or route column has an unexpected type.
    """
    route_id = _optional_route_id(truck_row)

    if route_id is None:
        truck = map_truck(truck_row)
        return HydratedTruckGraph(truck=truck, route=None)

    route_graph = route_graphs.get(route_id)
    if route_graph is None:
        route_graph = load_route_graph_tx(cursor, route_id)
        if route_graph is None:
            raise ValueError(f"Truck {truck_row['vehicle_id']} references missing route {route_id}.")
        route_graphs[route_id] = route_graph

    truck = route_graph.truck
    if truck is None or truck.vehicle_id != truck_row["vehicle_id"]:
        raise ValueError(
            f"Truck {truck_row['vehicle_id']} has route_id={route_id} in the database "
            f"but was not found as route {route_id}'s assigned truck. "
            "This indicates inconsistent truck-route hydration."
        )

    return HydratedTruckGraph(truck=truck, route=route_graph.route)


def _optional_route_id(row: RowDict) -> int | None:
    """Extract an optional route_id from a truck row, validating type and consistency.

    Args:
        row: Truck row to extract from.

    Returns:
        route_id value if present, or `None` if the truck is unassigned.

    Raises:
        TypeError: If the route_id column has an unexpected type.
    """
    value = row["route_id"]

    if value is None:
        return None

    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"route_id: expected int or None, got {type(value).__name__}")

    return value
