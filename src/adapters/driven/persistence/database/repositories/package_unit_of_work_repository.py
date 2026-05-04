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
                package.route.route_id if package.route is not None else None,
                package.package_id,
            ),
        )
        if affected != 1:
            raise ValueError(
                f"Expected to update one package row for id {package.package_id}, affected {affected}."
            )
