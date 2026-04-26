"""Use case for listing routes currently in progress."""

from datetime import datetime

from src.domain.entities.delivery_route import DeliveryRoute, RoutePosition
from src.ports.output.route_repository import RouteRepositoryPort


class ViewRoutesInProgressUseCase:
    """List routes that are currently active at the supplied time."""

    def __init__(self, routes: RouteRepositoryPort) -> None:
        """Initialize the use case.

        Args:
            routes: Repository used to list routes.
        """
        self._routes = routes

    def execute(self, now: datetime) -> list[tuple[DeliveryRoute, RoutePosition]]:
        """Return routes currently at a stop or in transit.

        Args:
            now: Clock value used to compute each route's position.

        Returns:
            A list of `(route, position)` tuples for active routes.
        """
        active: list[tuple[DeliveryRoute, RoutePosition]] = []

        for route in self._routes.list_all():
            pos = route.current_position(now)
            if pos.kind in {"AT_STOP", "IN_TRANSIT"}:
                active.append((route, pos))

        return active
