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

    def list_unassigned(self) -> list[DeliveryPackage]:
        """Return packages that are not assigned to a route."""
        return [package for package in self.list_all() if package.route is None]

    def replace_packages(self, packages_by_id: Mapping[int, DeliveryPackage], next_id: int) -> None:
        """Replace the full package state from a snapshot load.

        Args:
            packages_by_id: Replacement packages keyed by id.
            next_id: Next package id counter to restore.
        """
        self._packages = dict(packages_by_id)
        self._next_id = next_id
