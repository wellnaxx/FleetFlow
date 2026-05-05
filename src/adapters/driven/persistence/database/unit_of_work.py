"""Postgres unit-of-work implementation."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.adapters.driven.persistence.database.connection import get_connection
from src.adapters.driven.persistence.database.errors import DatabaseError
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

    from psycopg import Connection, Cursor

    from src.adapters.driven.persistence.database.executor import Row
    from src.ports.output.unit_of_work import (
        UnitOfWorkPackageRepositoryPort,
        UnitOfWorkRouteRepositoryPort,
        UnitOfWorkTruckRepositoryPort,
    )

logger = logging.getLogger(__name__)


class PostgresUnitOfWork:
    """Coordinate atomic persistence across multiple Postgres repositories."""

    routes: UnitOfWorkRouteRepositoryPort
    packages: UnitOfWorkPackageRepositoryPort
    trucks: UnitOfWorkTruckRepositoryPort

    _conn: Connection[Row]
    _cursor: Cursor[Row]
    _committed: bool

    def __enter__(self) -> PostgresUnitOfWork:
        """Open a database transaction and transaction-bound repositories.

        Returns:
            Active unit of work with transaction-bound repositories.

        Raises:
            DatabaseError: If opening the connection, cursor, or repositories fails.
        """
        conn: Connection[Row] | None = None
        cursor: Cursor[Row] | None = None

        try:
            conn = get_connection()
            cursor = conn.cursor()

            self.routes = PostgresRouteUnitOfWorkRepository(cursor)
            self.packages = PostgresPackageUnitOfWorkRepository(cursor)
            self.trucks = PostgresTruckUnitOfWorkRepository(cursor)

            self._conn = conn
            self._cursor = cursor
            self._committed = False
        except DatabaseError:
            self._close_resources(cursor=cursor, conn=conn)
            raise
        except Exception as exc:
            self._close_resources(cursor=cursor, conn=conn)
            logger.exception("Failed to open Postgres unit of work.")
            raise DatabaseError.operation_failed(exc) from exc
        else:
            return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Rollback uncommitted work and close database resources.

        Args:
            exc_type: Exception type when the context exits with an error.
            exc: Exception instance when the context exits with an error.
            tb: Traceback when the context exits with an error.

        Returns:
            None.

        Raises:
            Exception: The original rollback error when rollback fails during a clean exit.
        """
        rollback_error: Exception | None = None

        try:
            if not self._committed:
                try:
                    self.rollback()
                except Exception as error:
                    rollback_error = error
                    logger.exception("Failed to rollback Postgres unit of work.")
        finally:
            self._close_resources(cursor=self._cursor, conn=self._conn)

        if exc_type is None and rollback_error is not None:
            raise rollback_error

    def commit(self) -> None:
        """Commit all work performed inside the unit of work.

        Returns:
            None.

        Raises:
            DatabaseError: If the commit fails.
        """
        try:
            self._conn.commit()
            self._committed = True
        except DatabaseError:
            raise
        except Exception as exc:
            logger.exception("Failed to commit Postgres unit of work.")
            raise DatabaseError.operation_failed(exc) from exc

    def rollback(self) -> None:
        """Rollback all uncommitted work performed inside the unit of work.

        Returns:
            None.

        Raises:
            DatabaseError: If the rollback fails.
        """
        try:
            self._conn.rollback()
        except DatabaseError:
            raise
        except Exception as exc:
            logger.exception("Failed to rollback Postgres unit of work.")
            raise DatabaseError.operation_failed(exc) from exc

    @staticmethod
    def _close_resources(cursor: Cursor[Row] | None, conn: Connection[Row] | None) -> None:
        """Close cursor and connection, logging close failures.

        Args:
            cursor: Cursor to close, if one was opened.
            conn: Connection to close, if one was opened.

        Returns:
            None.
        """
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                logger.exception("Failed to close Postgres unit-of-work cursor.")

        if conn is not None:
            try:
                conn.close()
            except Exception:
                logger.exception("Failed to close Postgres unit-of-work connection.")
