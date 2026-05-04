from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from src.adapters.driven.persistence.database.connection import get_connection
from src.adapters.driven.persistence.database.repositories.package_unit_of_work_repository import (
    PostgresPackageUnitOfWorkRepository,
)
from src.adapters.driven.persistence.database.repositories.route_unit_of_work_repository import (
    PostgresRouteUnitOfWorkRepository,
)
from src.adapters.driven.persistence.database.repositories.truck_unit_of_work_repository import (
    PostgresTruckUnitOfWorkRepository,
)

if TYPE_CHECKING:
    from types import TracebackType

    from src.ports.output.unit_of_work import (
        UnitOfWorkPackageRepositoryPort,
        UnitOfWorkRouteRepositoryPort,
        UnitOfWorkTruckRepositoryPort,
    )

logger = logging.getLogger(__name__)


class PostgresUnitOfWork:
    """Coordinate atomic persistence across multiple repositories."""

    routes: UnitOfWorkRouteRepositoryPort
    packages: UnitOfWorkPackageRepositoryPort
    trucks: UnitOfWorkTruckRepositoryPort

    def __enter__(self) -> PostgresUnitOfWork:
        """Begin a unit-of-work boundary.

        Returns:
            Active unit of work with transaction-bound repositories.

        Raises:
            DatabaseError: If opening the connection or cursor fails.
        """
        conn = get_connection()
        cursor = None
        try:
            cursor = conn.cursor()
            self.routes = PostgresRouteUnitOfWorkRepository(cursor)
            self.packages = PostgresPackageUnitOfWorkRepository(cursor)
            self.trucks = PostgresTruckUnitOfWorkRepository(cursor)
        except Exception:
            self._close_resources(cursor=cursor, conn=conn)
            raise

        self._conn = conn
        self._cursor = cursor
        self._committed = False
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Close the transaction resources and rollback uncommitted work.

        Args:
            exc_type: Exception type when the context exits with an error.
            exc: Exception instance when the context exits with an error.
            tb: Traceback when the context exits with an error.

        Returns:
            None.
        """
        rollback_error: Exception | None = None
        try:
            if not self._committed:
                try:
                    self.rollback()
                except Exception as error:
                    rollback_error = error
                    logger.exception("Failed to rollback Postgres unit of work")
        finally:
            self._close_resources(cursor=self._cursor, conn=self._conn)

        if exc_type is None and rollback_error is not None:
            raise rollback_error

    def commit(self) -> None:
        """Commit all work performed inside the boundary."""
        self._conn.commit()
        self._committed = True

    def rollback(self) -> None:
        """Rollback all uncommitted work performed inside the boundary."""
        self._conn.rollback()

    @staticmethod
    def _close_resources(cursor: Any | None, conn: Any) -> None:
        """Close cursor and connection, attempting both even if one close fails.

        Args:
            cursor: Cursor to close, if it was created.
            conn: Connection to close.

        Returns:
            None.
        """
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                logger.exception("Failed to close Postgres unit-of-work cursor")

        try:
            conn.close()
        except Exception:
            logger.exception("Failed to close Postgres unit-of-work connection")
