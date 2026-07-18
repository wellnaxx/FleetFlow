"""Low-level database helpers for executing SQL against the Postgres backend.

Usage contract:
- For single-statement operations, use fetch_all, fetch_one, execute_insert,
  or execute_write. Each helper opens its own connection.
- For multi-statement atomic operations, use transaction_cursor and the _tx
  variants inside it.
- Do not mix standalone helpers and _tx helpers in the same logical operation.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import TYPE_CHECKING, cast

from psycopg.abc import QueryNoTemplate

from src.adapters.driven.persistence.database.connection import get_connection
from src.adapters.driven.persistence.database.errors import DatabaseError
from src.shared.validation import require_int

if TYPE_CHECKING:
    from collections.abc import Generator

    from psycopg import Cursor

logger = logging.getLogger(__name__)

type SQLParams = tuple[object, ...]
type SQLQuery = str | QueryNoTemplate
type Row = tuple[object, ...]
type RowDict = dict[str, object]


def _as_query(sql: SQLQuery) -> QueryNoTemplate:
    """Cast SQLQuery to QueryNoTemplate for psycopg's execute signature.

    psycopg accepts plain str at runtime but its stubs type execute() as
    QueryNoTemplate only. This cast bridges the gap without a runtime cost.
    """
    return cast("QueryNoTemplate", sql)


def _get_column_names(cursor: Cursor[Row]) -> list[str]:
    if cursor.description is None:
        raise DatabaseError.wrong_query_result()

    return [column.name for column in cursor.description]


def _extract_inserted_id(row: Row | None) -> int:
    if row is None:
        raise DatabaseError.missing_returning_id()

    new_id = row[0]
    try:
        return require_int(new_id, "returned_id")
    except TypeError as exc:
        raise DatabaseError.invalid_returned_id_type(new_id) from exc


def _cursor_to_dicts(cursor: Cursor[Row]) -> list[RowDict]:
    columns = _get_column_names(cursor)
    rows = cursor.fetchall()
    return [dict(zip(columns, row, strict=True)) for row in rows]


def _cursor_to_dict(cursor: Cursor[Row], row: Row | None) -> RowDict | None:
    if row is None:
        return None

    columns = _get_column_names(cursor)
    return dict(zip(columns, row, strict=True))


def _log_statement(kind: str, sql: SQLQuery, params: SQLParams) -> None:
    """Log database statement metadata without leaking parameter values."""
    logger.debug("%s statement with %d param(s): %s", kind, len(params), sql)


@contextmanager
def _db_operation(label: str) -> Generator[None]:
    """Wrap a database operation with consistent exception handling."""
    try:
        yield
    except DatabaseError:
        raise
    except Exception as exc:
        logger.exception("Database %s failed", label)
        raise DatabaseError.operation_failed(exc) from exc


@contextmanager
def transaction_cursor() -> Generator[Cursor[Row]]:
    """Yield a cursor inside one transaction.

    The transaction commits on normal exit and rolls back on exception.
    """
    try:
        with get_connection() as conn, conn.cursor() as cursor:
            try:
                logger.debug("Starting PostgreSQL transaction.")
                yield cursor
                conn.commit()
                logger.debug("Committed PostgreSQL transaction.")
            except Exception:
                conn.rollback()
                logger.debug("Rolled back PostgreSQL transaction.")
                raise
    except DatabaseError:
        raise
    except Exception as exc:
        logger.exception("Transactional database operation failed.")
        raise DatabaseError.operation_failed(exc) from exc


def fetch_all_tx(cursor: Cursor[Row], sql: SQLQuery, params: SQLParams = ()) -> list[RowDict]:
    """Execute a SELECT inside an open transaction and return all rows as dicts."""
    _log_statement("SELECT tx", sql, params)
    cursor.execute(_as_query(sql), params)
    return _cursor_to_dicts(cursor)


def fetch_one_tx(cursor: Cursor[Row], sql: SQLQuery, params: SQLParams = ()) -> RowDict | None:
    """Execute a SELECT inside an open transaction and return one row as a dict."""
    _log_statement("SELECT one tx", sql, params)
    cursor.execute(_as_query(sql), params)
    return _cursor_to_dict(cursor, cursor.fetchone())


def execute_insert_tx(cursor: Cursor[Row], sql: SQLQuery, params: SQLParams = ()) -> int:
    """Execute an INSERT inside an open transaction and return the inserted id.

    The SQL must include a RETURNING clause with the id as the first column.
    """
    _log_statement("INSERT tx", sql, params)
    cursor.execute(_as_query(sql), params)
    return _extract_inserted_id(cursor.fetchone())


def execute_write_tx(cursor: Cursor[Row], sql: SQLQuery, params: SQLParams = ()) -> int:
    """Execute an UPDATE or DELETE inside an open transaction and return affected row count."""
    _log_statement("WRITE tx", sql, params)
    cursor.execute(_as_query(sql), params)
    return int(cursor.rowcount)


def fetch_all(sql: SQLQuery, params: SQLParams = ()) -> list[RowDict]:
    """Execute a SELECT and return all rows as dicts."""
    _log_statement("SELECT", sql, params)
    with _db_operation("read"), get_connection() as conn, conn.cursor() as cursor:
        cursor.execute(_as_query(sql), params)
        return _cursor_to_dicts(cursor)


def fetch_one(sql: SQLQuery, params: SQLParams = ()) -> RowDict | None:
    """Execute a SELECT and return the first row as a dict, or None."""
    _log_statement("SELECT one", sql, params)
    with _db_operation("read"), get_connection() as conn, conn.cursor() as cursor:
        cursor.execute(_as_query(sql), params)
        return _cursor_to_dict(cursor, cursor.fetchone())


def execute_insert(sql: SQLQuery, params: SQLParams = ()) -> int:
    """Execute an INSERT and return the new row's id.

    The SQL must include a RETURNING clause that yields the new id as the first column.
    """
    _log_statement("INSERT", sql, params)
    with _db_operation("insert"), get_connection() as conn, conn.cursor() as cursor:
        cursor.execute(_as_query(sql), params)
        new_id = _extract_inserted_id(cursor.fetchone())
        conn.commit()
        return new_id


def execute_write(sql: SQLQuery, params: SQLParams = ()) -> int:
    """Execute an UPDATE or DELETE and return affected row count."""
    _log_statement("WRITE", sql, params)
    with _db_operation("write"), get_connection() as conn, conn.cursor() as cursor:
        cursor.execute(_as_query(sql), params)
        affected = cursor.rowcount
        conn.commit()
        return int(affected)


def execute_returning_one(sql: SQLQuery, params: SQLParams = ()) -> RowDict | None:
    """Execute a write query with RETURNING and return the first row as a dict, or None."""
    _log_statement("WRITE returning one", sql, params)
    with _db_operation("write"), get_connection() as conn, conn.cursor() as cursor:
        cursor.execute(_as_query(sql), params)
        row = _cursor_to_dict(cursor, cursor.fetchone())
        conn.commit()
        return row
