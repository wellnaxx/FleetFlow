from datetime import datetime

from src.domain.entities.delivery_route import DeliveryRoute, RoutePosition
from src.ports.output.route_repository import RouteRepositoryPort


class ViewRoutesInProgressUseCase:
    def __init__(self, routes: RouteRepositoryPort) -> None:
        self._routes = routes

    def execute(self, now: datetime) -> list[tuple[DeliveryRoute, RoutePosition]]:
        active: list[tuple[DeliveryRoute, RoutePosition]] = []

        for route in self._routes.list_all():
            pos = route.current_position(now)
            if pos.kind in {"AT_STOP", "IN_TRANSIT"}:
                active.append((route, pos))

        return active