from src.adapters.driven.persistence.database.executor import (
    execute_insert,
    execute_write,
    fetch_one,
)
from src.adapters.driven.persistence.database.graph_loaders.package_graph_loader import (
    load_package_graph,
    load_package_graph_page,
    load_package_graph_page_with_total,
    load_package_graphs,
    load_unassigned_package_graph_page,
    load_unassigned_package_graph_page_with_total,
    load_unassigned_package_graphs,
)
from src.adapters.driven.persistence.database.graph_loaders.route_graph_loader import load_route_graph
from src.adapters.driven.persistence.database.queries import QUERIES
from src.domain.entities.customer import Customer
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.enums.item_status import ItemStatus
from src.domain.value_objects.location_code import LocationCode


class PostgresPackageRepository:
    """Postgres-backed package repository implementation."""

    def create(
        self, start_location: LocationCode, end_location: LocationCode, weight: float, customer: Customer
    ) -> DeliveryPackage:
        """Create and persist a delivery package.

        Args:
            start_location: Pickup location code.
            end_location: Delivery location code.
            weight: Package weight in kilograms.
            customer: Persisted owning customer.

        Returns:
            Persisted delivery package with its database-allocated id.

        Raises:
            DatabaseError: If the insert fails or does not return an id.
            ValueError: If package construction fails.
        """
        package_id = execute_insert(
            QUERIES.packages.add,
            (str(start_location), str(end_location), weight, customer.customer_id),
        )

        return DeliveryPackage(
            start_location=start_location,
            end_location=end_location,
            weight=weight,
            customer=customer,
            package_id=package_id,
        )

    def remove(self, package_id: int) -> None:
        """Remove a package by id.

        Args:
            package_id: Package id to remove.

        Returns:
            None.

        Raises:
            DatabaseError: If the delete operation fails.
        """
        execute_write(QUERIES.packages.remove, (package_id,))

    def get_by_id(self, package_id: int) -> DeliveryPackage | None:
        """Return a package by id.

        Args:
            package_id: Package id to look up.

        Returns:
            Matching package, or `None` when no row exists.

        Raises:
            DatabaseError: If a select operation fails.
            KeyError: If a required package or customer column is missing.
            TypeError: If a required package or customer column has an unexpected type.
            ValueError: If persisted package data is invalid or references a missing customer.
        """
        package_graph = load_package_graph(package_id)
        return package_graph.package if package_graph is not None else None

    def list_all(self) -> list[DeliveryPackage]:
        """Return all packages.

        Returns:
            All persisted packages ordered by package id.

        Raises:
            DatabaseError: If the select operation fails.
            KeyError: If a required package or joined customer column is missing.
            TypeError: If a required package or joined customer column has an unexpected type.
            ValueError: If persisted package or customer data is invalid.
        """
        return [graph.package for graph in load_package_graphs()]

    def list_page(self, limit: int, offset: int) -> list[DeliveryPackage]:
        """Return a limited page of packages.

        Args:
            limit: Maximum number of packages to return.
            offset: Number of packages to skip.

        Returns:
            Persisted packages in the requested page ordered by package id.

        Raises:
            DatabaseError: If the select operation fails.
            KeyError: If a required package or joined customer column is missing.
            TypeError: If a required package or joined customer column has an unexpected type.
            ValueError: If persisted package or customer data is invalid.
        """
        return [graph.package for graph in load_package_graph_page(limit, offset)]

    def list_page_with_total(self, limit: int, offset: int) -> tuple[list[DeliveryPackage], int]:
        """Return a package page and total count from one database query."""
        graphs, total = load_package_graph_page_with_total(limit, offset)
        return [graph.package for graph in graphs], total

    def count_all(self) -> int:
        """Return the total number of packages."""
        row = fetch_one(QUERIES.packages.count_all)
        if row is None:
            return 0

        total = row["total"]
        if not isinstance(total, int) or isinstance(total, bool):
            raise TypeError("Package count must be an integer.")
        return total

    def list_unassigned(self) -> list[DeliveryPackage]:
        """Return packages that are not assigned to a route.

        Returns:
            Persisted unassigned packages ordered by package id.

        Raises:
            DatabaseError: If the select operation fails.
            KeyError: If a required package or joined customer column is missing.
            TypeError: If a required package or joined customer column has an unexpected type.
            ValueError: If persisted package or customer data is invalid.
        """
        return [graph.package for graph in load_unassigned_package_graphs()]

    def list_unassigned_page(self, limit: int, offset: int) -> list[DeliveryPackage]:
        """Return a limited page of unassigned packages.

        Args:
            limit: Maximum number of packages to return.
            offset: Number of packages to skip.

        Returns:
            Persisted unassigned packages in the requested page ordered by package id.

        Raises:
            DatabaseError: If the select operation fails.
            KeyError: If a required package or joined customer column is missing.
            TypeError: If a required package or joined customer column has an unexpected type.
            ValueError: If persisted package or customer data is invalid.
        """
        return [graph.package for graph in load_unassigned_package_graph_page(limit, offset)]

    def list_unassigned_page_with_total(
        self, limit: int, offset: int
    ) -> tuple[list[DeliveryPackage], int]:
        """Return an unassigned package page and total from one database query."""
        graphs, total = load_unassigned_package_graph_page_with_total(limit, offset)
        return [graph.package for graph in graphs], total

    def count_unassigned(self) -> int:
        """Return the total number of unassigned packages."""
        row = fetch_one(QUERIES.packages.count_unassigned, (ItemStatus.TODO.value,))
        if row is None:
            return 0

        total = row["total"]
        if not isinstance(total, int) or isinstance(total, bool):
            raise TypeError("Unassigned package count must be an integer.")
        return total

    def list_by_route(self, route_id: int) -> list[DeliveryPackage]:
        """Return packages assigned to a route.

        Args:
            route_id: Route id to look up.

        Returns:
            Persisted packages assigned to the route, ordered by package id.

        Raises:
            DatabaseError: If the select operation fails.
            KeyError: If a required package or joined customer column is missing.
            TypeError: If a required package or joined customer column has an unexpected type.
            ValueError: If persisted package or customer data is invalid.
        """
        route = load_route_graph(route_id)
        if route is None:
            return []
        return sorted(route.packages.values(), key=lambda package: package.package_id)

    def update_state(self, package: DeliveryPackage) -> None:
        """Persist mutable package runtime state.

        Args:
            package: Package whose current runtime state should be persisted.

        Returns:
            None.

        Raises:
            DatabaseError: If the update operation fails.
        """
        route_id = package.route.route_id if package.route is not None else None
        execute_write(
            QUERIES.packages.update_state,
            (
                package.status.value,
                str(package.current_location),
                package.expected_arrival,
                route_id,
                package.package_id,
            ),
        )
