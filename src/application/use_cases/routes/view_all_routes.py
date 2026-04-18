from src.domain.entities.delivery_route import DeliveryRoute
from src.ports.output.route_repository import RouteRepositoryPort


class ViewAllRoutesUseCase:
    def __init__(self, routes: RouteRepositoryPort) -> None:
        self._routes = routes

    def execute(self) -> list[DeliveryRoute]:
        return self._routes.list_all()