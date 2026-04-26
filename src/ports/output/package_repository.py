"""Output port for package repository adapters."""

from typing import Protocol

from src.domain.entities.delivery_package import DeliveryPackage


class PackageRepositoryPort(Protocol):
    """Persist and query delivery packages."""

    def peek_next_id(self) -> int:
        """Return the id that will be assigned to the next package."""
        ...

    def add(self, package: DeliveryPackage) -> None:
        """Persist a delivery package.

        Args:
            package: Package to store.
        """
        ...

    def remove(self, package_id: int) -> None:
        """Remove a package by id.

        Args:
            package_id: Package id to remove.
        """
        ...

    def get_by_id(self, package_id: int) -> DeliveryPackage | None:
        """Return a package by id, or `None` when absent.

        Args:
            package_id: Package id to look up.

        Returns:
            Matching package, or `None`.
        """
        ...

    def list_all(self) -> list[DeliveryPackage]:
        """Return all packages."""
        ...

    def list_unassigned(self) -> list[DeliveryPackage]:
        """Return packages that are not assigned to a route."""
        ...
