from src.domain.entities.delivery_route import DeliveryRoute


class InMemoryRouteRepository:
    def __init__(self) -> None:
        self._routes: dict[int, DeliveryRoute] = {}

    def next_id(self) -> int:
        if not self._routes:
            return 1
        return max(self._routes.keys()) + 1
    
    def add(self, route: DeliveryRoute) -> None:
        self._routes[route.route_id] = route

    def remove(self, route_id: int) -> None:
        if route_id in self._routes:
            del self._routes[route_id]

    def get_by_id(self, route_id: int) -> DeliveryRoute | None:
        return self._routes.get(route_id)
    
    def list_all(self) -> list[DeliveryRoute]:
        return list(self._routes.values())