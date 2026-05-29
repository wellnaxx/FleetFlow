from collections.abc import Sequence
from datetime import datetime

from src.adapters.driven.persistence.database.executor import (
    execute_insert_tx,
    execute_write,
    execute_write_tx,
    fetch_one,
    transaction_cursor,
)
from src.adapters.driven.persistence.database.graph_loaders.route_graph_loader import (
    load_route_graph,
    load_route_graph_page,
    load_route_graph_page_with_total,
    load_route_graphs,
)
from src.adapters.driven.persistence.database.queries import QUERIES
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.value_objects.location_code import LocationCode


class PostgresRouteRepository:
    """Postgres-backed route repository implementation."""

    def create(self, locations: Sequence[str | LocationCode], departure_time: datetime | None) -> DeliveryRoute:
        """Create and persist a route and its ordered stops atomically.

        Args:
            locations: Ordered route stops.
            departure_time: Optional scheduled departure time.

        Returns:
            Persisted route with its database-allocated id.

        Raises:
            DatabaseError: If the transaction, route insert, or stop insert fails.
            DomainValidationError: If route construction fails.
        """
        validated_route = DeliveryRoute(*locations, departure_time=departure_time, route_id=0)
        with transaction_cursor() as cursor:
            route_id = execute_insert_tx(
                cursor, QUERIES.routes.add, (departure_time, validated_route.status.value)
            )

            for stop_order, location in enumerate(validated_route.locations):
                execute_write_tx(cursor, QUERIES.routes.add_stop, (route_id, stop_order, str(location)))

        return DeliveryRoute(*validated_route.locations, departure_time=departure_time, route_id=route_id)

    def remove(self, route_id: int) -> None:
        """Remove a route by id.

        Args:
            route_id: Route id to remove.

        Returns:
            None.

        Raises:
            DatabaseError: If the delete operation fails.
        """
        execute_write(QUERIES.routes.remove, (route_id,))

    def get_by_id(self, route_id: int) -> DeliveryRoute | None:
        """Return a route by id.

        Args:
            route_id: Route id to look up.

        Returns:
            Matching route, or `None` when no row exists.

        Raises:
            DatabaseError: If the select operation fails.
            KeyError: If a required route or stop column is missing.
            TypeError: If a required route or stop column has an unexpected type.
            ValueError: If persisted route data is invalid.
        """
        route_graph = load_route_graph(route_id)
        return route_graph.route if route_graph is not None else None

    def list_all(self) -> list[DeliveryRoute]:
        """Return all routes.

        Returns:
            All persisted routes ordered by route id.

        Raises:
            DatabaseError: If the select operation fails.
            KeyError: If a required route or stop column is missing.
            TypeError: If a required route or stop column has an unexpected type.
            ValueError: If persisted route data is invalid.
        """
        return [graph.route for graph in load_route_graphs()]

    def list_page(self, limit: int, offset: int) -> list[DeliveryRoute]:
        """Return a limited page of routes ordered by route id."""
        return [graph.route for graph in load_route_graph_page(limit, offset)]

    def list_page_with_total(self, limit: int, offset: int) -> tuple[list[DeliveryRoute], int]:
        """Return a route page and total count from one repository operation."""
        graphs, total = load_route_graph_page_with_total(limit, offset)
        return [graph.route for graph in graphs], total

    def count_all(self) -> int:
        """Return the total number of routes."""
        row = fetch_one(QUERIES.routes.count_all)
        if row is None:
            return 0

        total = row["total"]
        if not isinstance(total, int) or isinstance(total, bool):
            raise TypeError("Route count must be an integer.")
        return total

    def update_state(self, route: DeliveryRoute) -> None:
        """Persist mutable route runtime state.

        Args:
            route: Route whose current runtime state should be persisted.

        Returns:
            None.

        Raises:
            DatabaseError: If the update operation fails.
        """
        truck_vehicle_id = route.truck.vehicle_id if route.truck is not None else None
        execute_write(
            QUERIES.routes.update_state,
            (
                route.departure_time,
                route.status.value,
                truck_vehicle_id,
                route.route_id,
            ),
        )
