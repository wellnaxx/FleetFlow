"""Output port for route repository adapters."""

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.value_objects.location_code import LocationCode


class RouteRepositoryPort(Protocol):
    """Persist and query delivery routes."""

    def create(
        self,
        locations: Sequence[str | LocationCode],
        departure_time: datetime | None,
    ) -> DeliveryRoute:
        """Create and persist a delivery route.

        Args:
            locations: Ordered route stops.
            departure_time: Optional scheduled departure time.

        Returns:
            Persisted route with its allocated id.
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

    def list_page(self, limit: int, offset: int) -> list[DeliveryRoute]:
        """Return a limited page of routes.

        Args:
            limit: Maximum number of routes to return.
            offset: Number of routes to skip.

        Returns:
            Routes in the requested page.
        """
        ...

    def list_page_with_total(self, limit: int, offset: int) -> tuple[list[DeliveryRoute], int]:
        """Return a route page and total count from one repository operation.

        Args:
            limit: Maximum number of routes to return.
            offset: Number of routes to skip.

        Returns:
            Tuple of (routes in the requested page, total count of all routes).
        """
        ...

    def count_all(self) -> int:
        """Return the total number of routes."""
        ...

    def update_state(self, route: DeliveryRoute) -> None:
        """Persist mutable route runtime state.

        Args:
            route: Route whose current runtime state should be persisted.

        Returns:
            None.
        """
        ...
