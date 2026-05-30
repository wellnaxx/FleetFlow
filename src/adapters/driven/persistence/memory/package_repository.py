"""In-memory package repository implementation."""

from collections.abc import Mapping

from src.domain.entities.customer import Customer
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.value_objects.location_code import LocationCode


class InMemoryPackageRepository:
    """In-memory package repository keyed by package id.

    Normal package creation allocates ids inside `create()`. Snapshot restore
    and memory-only tests may still use `add()` to load an existing package id.
    """

    def __init__(self) -> None:
        """Initialize an empty package repository."""
        self._packages: dict[int, DeliveryPackage] = {}
        self._next_id: int = 1

    def peek_next_id(self) -> int:
        """Return the next memory id counter.

        This is intentionally not part of the shared package repository port;
        it exists for in-memory world-state snapshots.

        Returns:
            The current next id counter.
        """
        return self._next_id

    def create(
        self,
        start_location: LocationCode,
        end_location: LocationCode,
        weight: float,
        customer: Customer,
    ) -> DeliveryPackage:
        """Create and store a package with an in-memory allocated id.

        Args:
            start_location: Pickup location code.
            end_location: Delivery location code.
            weight: Package weight in kilograms.
            customer: Owning customer.

        Returns:
            Stored package with its allocated id.
        """
        package = DeliveryPackage(
            start_location=start_location,
            end_location=end_location,
            weight=weight,
            customer=customer,
            package_id=self._next_id,
        )
        self.add(package)
        return package

    def add(self, package: DeliveryPackage) -> DeliveryPackage:
        """Add an existing package and advance the memory id counter.

        Args:
            package: Package entity to store.


        Raises:
            ValueError: If a package with the same id already exists.
        """
        if package.package_id in self._packages:
            raise ValueError(f"Package with id {package.package_id} already exists.")
        self._packages[package.package_id] = package

        self._next_id = max(self._next_id, package.package_id + 1)
        return package

    def remove(self, package_id: int) -> None:
        """Remove a package by id if it exists.

        Args:
            package_id: Package id to remove.
        """
        if package_id in self._packages:
            del self._packages[package_id]

    def get_by_id(self, package_id: int) -> DeliveryPackage | None:
        """Return a package by id, if present.

        Args:
            package_id: Package id to look up.

        Returns:
            Matching package, or `None`.
        """
        return self._packages.get(package_id)

    def list_all(self) -> list[DeliveryPackage]:
        """Return all packages ordered by id."""
        return [self._packages[package_id] for package_id in sorted(self._packages)]

    def list_page(self, limit: int, offset: int) -> list[DeliveryPackage]:
        """Return a page of packages ordered by id.

        Args:
            limit: Maximum number of packages to return.
            offset: Number of packages to skip.

        Returns:
            Packages in the requested page.
        """
        return self.list_all()[offset : offset + limit]

    def list_page_with_total(self, limit: int, offset: int) -> tuple[list[DeliveryPackage], int]:
        """Return a package page and total count from the current memory snapshot."""
        packages = self.list_all()
        return packages[offset : offset + limit], len(packages)

    def count_all(self) -> int:
        """Return the total number of packages."""
        return len(self._packages)

    def list_unassigned(self) -> list[DeliveryPackage]:
        """Return packages that are not assigned to a route."""
        return [package for package in self.list_all() if package.route_id is None]

    def list_unassigned_page(self, limit: int, offset: int) -> list[DeliveryPackage]:
        """Return a page of unassigned packages ordered by id.

        Args:
            limit: Maximum number of packages to return.
            offset: Number of packages to skip.

        Returns:
            Unassigned packages in the requested page.
        """
        return self.list_unassigned()[offset : offset + limit]

    def list_unassigned_page_with_total(self, limit: int, offset: int) -> tuple[list[DeliveryPackage], int]:
        """Return an unassigned page and total count from the current memory snapshot."""
        packages = self.list_unassigned()
        return packages[offset : offset + limit], len(packages)

    def count_unassigned(self) -> int:
        """Return the total number of unassigned packages."""
        return sum(package.route_id is None for package in self._packages.values())

    def list_by_route(self, route_id: int) -> list[DeliveryPackage]:
        """Return packages that are assigned to a specific route.

        Args:
            route_id: Route id to look up.

        Returns:
            A list of matching packages.
        """
        return [
            package
            for package in self.list_all()
            if package.route_id == route_id
        ]

    def update_state(self, package: DeliveryPackage) -> None:
        """Persist mutable package runtime state.

        For the in-memory implementation, this is a no-op because stored
        packages are mutated by object reference.

        Args:
            package: Package whose current runtime state should be persisted.

        Returns:
            None.
        """

    def replace_packages(self, packages_by_id: Mapping[int, DeliveryPackage], next_id: int) -> None:
        """Replace the full package state from a snapshot load.

        Args:
            packages_by_id: Replacement packages keyed by id.
            next_id: Next package id counter to restore.
        """
        self._packages = dict(packages_by_id)
        self._next_id = next_id
