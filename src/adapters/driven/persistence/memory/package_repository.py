"""In-memory package repository implementation."""

from collections.abc import Mapping

from src.domain.entities.delivery_package import DeliveryPackage


class InMemoryPackageRepository:
    """In-memory package repository keyed by package id.

    Id allocation uses a peek-then-add model:
    `peek_next_id()` returns the current candidate id without reserving it, and
    `add()` commits id advancement by moving `_next_id` past the stored
    package's id.
    """

    def __init__(self) -> None:
        """Initialize an empty package repository."""
        self._packages: dict[int, DeliveryPackage] = {}
        self._next_id: int = 1

    def peek_next_id(self) -> int:
        """Return the next candidate package id without reserving it.

        This method is read-only. The returned id is not committed until a
        package with that id is successfully added to the repository.

        Returns:
            The current next candidate package id.
        """
        return self._next_id

    def add(self, package: DeliveryPackage) -> None:
        """Add a package and commit repository id advancement.

        The repository uses a peek-then-add allocation model: callers may inspect
        `peek_next_id()` to choose an id, but the id is not considered committed
        until `add()` succeeds.

        On successful add, `_next_id` is advanced so it remains greater than every
        stored package id.

        Args:
            package: Package entity to store.


        Raises:
            ValueError: If a package with the same id already exists.
        """
        if package.package_id in self._packages:
            raise ValueError(f"Package with id {package.package_id} already exists.")
        self._packages[package.package_id] = package

        self._next_id = max(self._next_id, package.package_id + 1)

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
