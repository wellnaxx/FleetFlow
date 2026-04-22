from src.domain.entities.delivery_route import DeliveryRoute


class InMemoryRouteRepository:
    def __init__(self) -> None:
        self._routes: dict[int, DeliveryRoute] = {}
        self._next_id = 1

    def peek_next_id(self) -> int:
        return self._next_id

    def add(self, route: DeliveryRoute) -> None:
        if route.route_id in self._routes:
            raise ValueError(f"Route with ID {route.route_id} already exists")
        self._routes[route.route_id] = route

        self._next_id = max(self._next_id, route.route_id + 1)

    def remove(self, route_id: int) -> None:
        if route_id in self._routes:
            del self._routes[route_id]

    def get_by_id(self, route_id: int) -> DeliveryRoute | None:
        return self._routes.get(route_id)

    def list_all(self) -> list[DeliveryRoute]:
        return [self._routes[route_id] for route_id in sorted(self._routes)]

    def replace_routes(self, routes_by_id: dict[int, DeliveryRoute], next_id: int) -> None:
        self._routes = dict(routes_by_id)
        self._next_id = next_id
