"""Database adapter exceptions."""

from __future__ import annotations


class DatabaseError(RuntimeError):
    """Base error for database adapter failures."""

    @classmethod
    def read_failed(cls, cause: Exception) -> DatabaseError:
        """Return an error describing a failed database read."""
        return cls(f"Database read failed: {cause}")

    @classmethod
    def insert_failed(cls, cause: Exception) -> DatabaseError:
        """Return an error describing a failed database insert."""
        return cls(f"Database insert failed: {cause}")

    @classmethod
    def write_failed(cls, cause: Exception) -> DatabaseError:
        """Return an error describing a failed database update or delete."""
        return cls(f"Database write failed: {cause}")

    @classmethod
    def operation_failed(cls, cause: Exception) -> DatabaseError:
        """Return an error describing a general database operation failure."""
        return cls(f"Database operation failed: {cause}")

    @classmethod
    def wrong_query_result(cls) -> DatabaseError:
        """Return an error for a query that did not expose result columns."""
        return cls("Database query did not return a result set.")

    @classmethod
    def missing_returning_id(cls) -> DatabaseError:
        """Return an error for an insert that omitted its returned identifier."""
        return cls("Database insert did not return an id. Did you forget RETURNING id?")

    @classmethod
    def invalid_returned_id_type(cls, value: object) -> DatabaseError:
        """Return an error for a non-integer identifier returned by PostgreSQL."""
        return cls(f"Database returned an invalid id value: {value!r}.")

    @classmethod
    def missing_query_row(cls, query_name: str) -> DatabaseError:
        """Return an error for a query contract that requires one row.

        Args:
            query_name: Human-readable query name included in the message.

        Returns:
            Database adapter error describing the missing row.
        """
        return cls(f"{query_name} query returned no row.")
