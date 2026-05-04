from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from types import TracebackType

    from src.domain.entities.delivery_package import DeliveryPackage
    from src.domain.entities.delivery_route import DeliveryRoute
    from src.domain.entities.truck import Truck


class UnitOfWorkRouteRepositoryPort(Protocol):
    """Route persistence operations available inside a unit of work."""

    def update_state(self, route: DeliveryRoute) -> None:
        """Persist mutable route runtime state.

        Args:
            route: Route whose current runtime state should be persisted.

        Returns:
            None.
        """
        ...

    def remove(self, route_id: int) -> None:
        """Remove a route by id.

        Args:
            route_id: Route id to remove.

        Returns:
            None.
        """
        ...


class UnitOfWorkPackageRepositoryPort(Protocol):
    """Package persistence operations available inside a unit of work."""

    def update_state(self, package: DeliveryPackage) -> None:
        """Persist mutable package runtime state.

        Args:
            package: Package whose current runtime state should be persisted.

        Returns:
            None.
        """
        ...


class UnitOfWorkTruckRepositoryPort(Protocol):
    """Truck persistence operations available inside a unit of work."""

    def update_state(self, truck: Truck) -> None:
        """Persist mutable truck runtime state.

        Args:
            truck: Truck whose current runtime state should be persisted.

        Returns:
            None.
        """
        ...


class UnitOfWorkPort(Protocol):
    """Coordinate atomic persistence across multiple repositories."""

    routes: UnitOfWorkRouteRepositoryPort
    packages: UnitOfWorkPackageRepositoryPort
    trucks: UnitOfWorkTruckRepositoryPort

    def __enter__(self) -> UnitOfWorkPort:
        """Begin a unit-of-work boundary."""
        ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Rollback uncommitted work when leaving with an exception."""
        ...

    def commit(self) -> None:
        """Commit all work performed inside the boundary."""
        ...

    def rollback(self) -> None:
        """Rollback all uncommitted work performed inside the boundary."""
        ...
