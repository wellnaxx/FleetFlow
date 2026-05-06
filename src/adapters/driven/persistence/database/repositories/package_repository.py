from src.adapters.driven.persistence.database.executor import (
    execute_insert,
    execute_write,
)
from src.adapters.driven.persistence.database.graph_loaders.world_graph_loader import load_world_graph
from src.adapters.driven.persistence.database.queries import QUERIES
from src.domain.entities.customer import Customer
from src.domain.entities.delivery_package import DeliveryPackage
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
        return load_world_graph().packages.get(package_id)

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
        return sorted(load_world_graph().packages.values(), key=lambda package: package.package_id)

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
        return sorted(
            (package for package in load_world_graph().packages.values() if package.route is None),
            key=lambda package: package.package_id,
        )

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
        route = load_world_graph().routes.get(route_id)
        if route is None:
            return []
        return sorted(route.packages, key=lambda package: package.package_id)

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
