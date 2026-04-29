"""In-memory route repository implementation."""

from collections.abc import Mapping, Sequence
from datetime import datetime

from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.value_objects.location_code import LocationCode


class InMemoryRouteRepository:
    """In-memory route repository keyed by route id.

    Normal route creation allocates ids inside `create()`. Snapshot restore
    and memory-only tests may still use `add()` to load an existing route id.
    """

    def __init__(self) -> None:
        """Initialize an empty route repository."""
        self._routes: dict[int, DeliveryRoute] = {}
        self._next_id = 1

    def peek_next_id(self) -> int:
        """Return the next memory id counter.

        This is intentionally not part of the shared route repository port;
        it exists for in-memory world-state snapshots.

        Returns:
            The current next id counter.
        """
        return self._next_id

    def create(
        self,
        locations: Sequence[str | LocationCode],
        departure_time: datetime | None,
    ) -> DeliveryRoute:
        """Create and store a route with an in-memory allocated id.

        Args:
            locations: Ordered route stops.
            departure_time: Optional scheduled departure time.

        Returns:
            Stored route with its allocated id.
        """
        route = DeliveryRoute(*locations, departure_time=departure_time, route_id=self._next_id)
        self.add(route)
        return route

    def add(self, route: DeliveryRoute) -> DeliveryRoute:
        """Add an existing route and advance the memory id counter.

        Args:
            route: Route entity to store.

        Raises:
            ValueError: If a route with the same id already exists.
        """
        if route.route_id in self._routes:
            raise ValueError(f"Route with ID {route.route_id} already exists")
        self._routes[route.route_id] = route

        self._next_id = max(self._next_id, route.route_id + 1)
        return route

    def remove(self, route_id: int) -> None:
        """Remove a route by id if it exists.

        Args:
            route_id: Route id to remove.
        """
        if route_id in self._routes:
            del self._routes[route_id]

    def get_by_id(self, route_id: int) -> DeliveryRoute | None:
        """Return a route by id, if present.

        Args:
            route_id: Route id to look up.

        Returns:
            Matching route, or `None`.
        """
        return self._routes.get(route_id)

    def list_all(self) -> list[DeliveryRoute]:
        """Return all routes ordered by id."""
        return [self._routes[route_id] for route_id in sorted(self._routes)]

    def replace_routes(self, routes_by_id: Mapping[int, DeliveryRoute], next_id: int) -> None:
        """Replace the full route state from a snapshot load.

        Args:
            routes_by_id: Replacement routes keyed by id.
            next_id: Next route id counter to restore.
        """
        self._routes = dict(routes_by_id)
        self._next_id = next_id
