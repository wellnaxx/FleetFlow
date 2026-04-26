"""Output port for route repository adapters."""

from typing import Protocol

from src.domain.entities.delivery_route import DeliveryRoute


class RouteRepositoryPort(Protocol):
    """Persist and query delivery routes."""

    def peek_next_id(self) -> int:
        """Return the id that will be assigned to the next route."""
        ...

    def add(self, route: DeliveryRoute) -> None:
        """Persist a delivery route.

        Args:
            route: Route to store.
        """
        ...

    def remove(self, route_id: int) -> None:
        """Remove a route by id.

        Args:
            route_id: Route id to remove.
        """
        ...

    def get_by_id(self, route_id: int) -> DeliveryRoute | None:
        """Return a route by id, or `None` when absent.

        Args:
            route_id: Route id to look up.

        Returns:
            Matching route, or `None`.
        """
        ...

    def list_all(self) -> list[DeliveryRoute]:
        """Return all routes."""
        ...
