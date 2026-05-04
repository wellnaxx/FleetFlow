from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import TracebackType

    from src.ports.output.unit_of_work import (
        UnitOfWorkPackageRepositoryPort,
        UnitOfWorkRouteRepositoryPort,
        UnitOfWorkTruckRepositoryPort,
    )


class InMemoryUnitOfWork:
    """Coordinate atomic persistence across multiple repositories."""
    def __init__(
        self,
        routes: UnitOfWorkRouteRepositoryPort,
        packages: UnitOfWorkPackageRepositoryPort,
        trucks: UnitOfWorkTruckRepositoryPort,
    ) -> None:
        """Initialize the unit of work with in-memory repositories.

        Args:
            routes: Route repository participating in the unit of work.
            packages: Package repository participating in the unit of work.
            trucks: Truck repository participating in the unit of work.
        """
        self.routes = routes
        self.packages = packages
        self.trucks = trucks

    def __enter__(self) -> InMemoryUnitOfWork:
        """Begin a unit-of-work boundary."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Rollback uncommitted work when leaving with an exception."""
        if exc_type:
            self.rollback()

    def commit(self) -> None:
        """Commit all work performed inside the boundary."""

    def rollback(self) -> None:
        """Rollback all uncommitted work performed inside the boundary."""
