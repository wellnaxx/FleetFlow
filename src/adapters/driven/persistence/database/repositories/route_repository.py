from collections.abc import Sequence
from datetime import datetime

from src.adapters.driven.persistence.database.executor import (
    RowDict,
    execute_insert_tx,
    execute_write,
    execute_write_tx,
    fetch_all,
    transaction_cursor,
)
from src.adapters.driven.persistence.database.mappers import map_route
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
        route_rows = fetch_all(QUERIES.routes.get_by_id, (route_id,))
        if not route_rows:
            return None

        return map_route(route_rows)

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
        rows = fetch_all(QUERIES.routes.list_all)
        groups: dict[int, list[RowDict]] = {}
        for row in rows:
            route_id = row["route_id"]
            if not isinstance(route_id, int):
                raise TypeError(f"route_id: expected int, got {type(route_id).__name__}")
            groups.setdefault(route_id, []).append(row)
        return [map_route(group) for group in groups.values()]
