from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from types import TracebackType

    from src.ports.output.package_repository import PackageRepositoryPort
    from src.ports.output.route_repository import RouteRepositoryPort
    from src.ports.output.truck_repository import TruckRepositoryPort


class UnitOfWorkPort(Protocol):
    """Coordinate atomic persistence across multiple repositories."""

    routes: RouteRepositoryPort
    packages: PackageRepositoryPort
    trucks: TruckRepositoryPort

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
