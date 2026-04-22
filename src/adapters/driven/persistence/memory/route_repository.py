from src.domain.entities.delivery_route import DeliveryRoute


class InMemoryRouteRepository:
    """Store routes in process memory for runtime use."""

    def __init__(self) -> None:
        self._routes: dict[int, DeliveryRoute] = {}
        self._next_id = 1

    def peek_next_id(self) -> int:
        """Return the next route id without incrementing the counter."""
        return self._next_id

    def add(self, route: DeliveryRoute) -> None:
        """Add a route to the repository.

        Args:
            route: Route entity to store.

        Raises:
            ValueError: If the route id already exists.
        """
        if route.route_id in self._routes:
            raise ValueError(f"Route with ID {route.route_id} already exists")
        self._routes[route.route_id] = route

        self._next_id = max(self._next_id, route.route_id + 1)

    def remove(self, route_id: int) -> None:
        """Remove a route by id if it exists."""
        if route_id in self._routes:
            del self._routes[route_id]

    def get_by_id(self, route_id: int) -> DeliveryRoute | None:
        """Return a route by id, if present."""
        return self._routes.get(route_id)

    def list_all(self) -> list[DeliveryRoute]:
        """Return all routes ordered by id."""
        return [self._routes[route_id] for route_id in sorted(self._routes)]

    def replace_routes(self, routes_by_id: dict[int, DeliveryRoute], next_id: int) -> None:
        """Replace the full route state from a snapshot load."""
        self._routes = dict(routes_by_id)
        self._next_id = next_id
