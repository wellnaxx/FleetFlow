"""In-memory route repository implementation."""

from collections.abc import Mapping

from src.domain.entities.delivery_route import DeliveryRoute


class InMemoryRouteRepository:
    """In-memory route repository keyed by route id.

    Id allocation uses a peek-then-add model:
    `peek_next_id()` returns the current candidate id without reserving it, and
    `add()` commits id advancement by moving `_next_id` past the stored
    route's id.
    """

    def __init__(self) -> None:
        """Initialize an empty route repository."""
        self._routes: dict[int, DeliveryRoute] = {}
        self._next_id = 1

    def peek_next_id(self) -> int:
        """Return the next candidate route id without reserving it.

        This method is read-only. The returned id is not committed until a
        route with that id is successfully added to the repository.

        Returns:
            The current next candidate route id.
        """
        return self._next_id

    def add(self, route: DeliveryRoute) -> None:
        """Add a route and commit repository id advancement.

        The repository uses a peek-then-add allocation model: callers may inspect
        `peek_next_id()` to choose an id, but the id is not considered committed
        until `add()` succeeds.

        On successful add, `_next_id` is advanced so it remains greater than every
        stored route id.

        Args:
            route: Route entity to store.

        Raises:
            ValueError: If a route with the same id already exists.
        """
        if route.route_id in self._routes:
            raise ValueError(f"Route with ID {route.route_id} already exists")
        self._routes[route.route_id] = route

        self._next_id = max(self._next_id, route.route_id + 1)

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
