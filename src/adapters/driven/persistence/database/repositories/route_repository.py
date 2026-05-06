from collections.abc import Sequence
from datetime import datetime

from src.adapters.driven.persistence.database.executor import (
    execute_insert_tx,
    execute_write,
    execute_write_tx,
    transaction_cursor,
)
from src.adapters.driven.persistence.database.graph_loaders.world_graph_loader import load_world_graph
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
            ValueError: If route construction fails.
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
        return load_world_graph().routes.get(route_id)

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
        return sorted(load_world_graph().routes.values(), key=lambda route: route.route_id)

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
