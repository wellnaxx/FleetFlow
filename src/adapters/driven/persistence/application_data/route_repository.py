from src.core.application_data import ApplicationData
from src.domain.entities.delivery_route import DeliveryRoute


class ApplicationDataRouteRepository:
    def __init__(self, app_data: ApplicationData) -> None:
        self._app_data = app_data

    def next_id(self) -> int:
        return self._app_data.allocate_route_id()
    
    def add(self, route: DeliveryRoute) -> None:
        routes = self._app_data.route_store
        if any(existing.route_id == route.route_id for existing in routes):
            raise ValueError(f"Route with ID {route.route_id} already exists")
        routes.append(route)

    def remove(self, route_id: int) -> None:
        routes = self._app_data.route_store
        for idx, route in enumerate(routes):
            if route.route_id == route_id:
                routes.pop(idx)
                return
            
    def get_by_id(self, route_id: int) -> DeliveryRoute | None:
        for route in self._app_data.route_store:
            if route.route_id == route_id:
                return route
        return None
    
    def list_all(self) -> list[DeliveryRoute]:
        return list(self._app_data.route_store)