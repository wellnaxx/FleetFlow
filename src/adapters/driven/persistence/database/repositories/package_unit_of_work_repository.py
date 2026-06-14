"""Transaction-bound package repository for Postgres unit-of-work operations."""

from psycopg import Cursor

from src.adapters.driven.persistence.database.executor import execute_write_tx
from src.adapters.driven.persistence.database.queries import QUERIES
from src.domain.entities.delivery_package import DeliveryPackage


class PostgresPackageUnitOfWorkRepository:
    """Persist package state using a shared transaction cursor."""

    def __init__(self, cursor: Cursor) -> None:
        """Initialize the repository with a transaction cursor.

        Args:
            cursor: Cursor owned by the active unit of work.
        """
        self._cursor = cursor

    def update_state(self, package: DeliveryPackage) -> None:
        """Persist mutable package runtime state.

        Args:
            package: Package whose current runtime state should be persisted.

        Returns:
            None.

        Raises:
            ValueError: If the package row no longer exists.
        """
        affected = execute_write_tx(
            self._cursor,
            QUERIES.packages.update_state,
            (
                package.status.value,
                str(package.current_location),
                package.expected_arrival,
                package.route_id,
                package.package_id,
            ),
        )
        if affected != 1:
            raise ValueError(
                f"Expected to update one package row for id {package.package_id}, affected {affected}."
            )

    def remove(self, package_id: int) -> None:
        """Remove a package by id inside the active transaction.

        Args:
            package_id: Package id to remove.

        Returns:
            None.

        Raises:
            DatabaseError: If the delete operation fails.
            ValueError: If the package row no longer exists.
        """
        affected = execute_write_tx(self._cursor, QUERIES.packages.remove, (package_id,))
        if affected != 1:
            raise ValueError(f"Expected to remove one package row for id {package_id}, affected {affected}.")
