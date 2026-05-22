"""Output port for package repository adapters."""

from typing import Protocol

from src.domain.entities.customer import Customer
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.value_objects.location_code import LocationCode


class PackageRepositoryPort(Protocol):
    """Persist and query delivery packages."""

    def create(
        self,
        start_location: LocationCode,
        end_location: LocationCode,
        weight: float,
        customer: Customer,
    ) -> DeliveryPackage:
        """Create and persist a delivery package.

        Args:
            start_location: Pickup location code.
            end_location: Delivery location code.
            weight: Package weight in kilograms.
            customer: Owning customer.

        Returns:
            Persisted delivery package with its allocated id.
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

    def list_page(self, limit: int, offset: int) -> list[DeliveryPackage]:
        """Return a limited page of packages.

        Args:
            limit: Maximum number of packages to return.
            offset: Number of packages to skip.

        Returns:
            Packages in the requested page.
        """
        ...

    def list_page_with_total(self, limit: int, offset: int) -> tuple[list[DeliveryPackage], int]:
        """Return a package page and total count from one repository operation."""
        ...

    def count_all(self) -> int:
        """Return the total number of packages."""
        ...

    def list_unassigned(self) -> list[DeliveryPackage]:
        """Return packages that are not assigned to a route."""
        ...

    def list_unassigned_page(self, limit: int, offset: int) -> list[DeliveryPackage]:
        """Return a limited page of unassigned packages.

        Args:
            limit: Maximum number of packages to return.
            offset: Number of packages to skip.

        Returns:
            Unassigned packages in the requested page.
        """
        ...

    def list_unassigned_page_with_total(
        self, limit: int, offset: int
    ) -> tuple[list[DeliveryPackage], int]:
        """Return an unassigned package page and total from one repository operation."""
        ...

    def count_unassigned(self) -> int:
        """Return the total number of unassigned packages."""
        ...

    def list_by_route(self, route_id: int) -> list[DeliveryPackage]:
        """Return packages that are assigned to a specific route.

        Args:
            route_id: Route id to look up.

        Returns:
            A list of matching packages.
        """
        ...

    def update_state(self, package: DeliveryPackage) -> None:
        """Persist mutable package runtime state.

        Args:
            package: Package whose current runtime state should be persisted.

        Returns:
            None.
        """
        ...
