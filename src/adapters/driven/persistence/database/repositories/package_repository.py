from src.adapters.driven.persistence.database.executor import (
    RowDict,
    execute_insert,
    execute_write,
    fetch_all,
    fetch_one,
)
from src.adapters.driven.persistence.database.mappers import map_customer, map_package
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
        package_row = fetch_one(QUERIES.packages.get_by_id, (package_id,))
        if package_row is None:
            return None

        customer_id = _package_customer_id(package_row)
        customer_row = fetch_one(QUERIES.customers.get_by_id, (customer_id,))
        if customer_row is None:
            raise ValueError(f"Package {package_id} references missing customer {customer_id}.")
        customer = map_customer(customer_row)

        return map_package(package_row, customer)

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
        package_rows = fetch_all(QUERIES.packages.list_all)
        return [_map_joined_package_row(package_row) for package_row in package_rows]

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
        package_rows = fetch_all(QUERIES.packages.list_unassigned)
        return [_map_joined_package_row(package_row) for package_row in package_rows]

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
        package_rows = fetch_all(QUERIES.packages.list_by_route, (route_id,))
        return [_map_joined_package_row(package_row) for package_row in package_rows]

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


def _map_joined_package_row(row: RowDict) -> DeliveryPackage:
    """Map a package row that includes joined customer columns.

    Args:
        row: Package row with `customer_name`, `customer_email`, and `customer_phone` aliases.

    Returns:
        Delivery package built with its customer.

    Raises:
        KeyError: If a required package or joined customer column is missing.
        TypeError: If a required package or joined customer column has an unexpected type.
        ValueError: If persisted package or customer data is invalid.
    """
    customer = map_customer(
        {
            "customer_id": row["customer_id"],
            "name": row["customer_name"],
            "email": row["customer_email"],
            "phone": row["customer_phone"],
        }
    )
    return map_package(row, customer)


def _package_customer_id(row: RowDict) -> int:
    """Return the customer id from a package row.

    Args:
        row: Package row returned by the executor.

    Returns:
        Customer id referenced by the package row.

    Raises:
        KeyError: If the customer id column is missing.
        TypeError: If the customer id column is not an integer.
    """
    customer_id = row["customer_id"]
    if not isinstance(customer_id, int):
        raise TypeError(f"customer_id: expected int, got {type(customer_id).__name__}")
    return customer_id
