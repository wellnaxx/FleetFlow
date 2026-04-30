"""Database adapter exceptions."""
from __future__ import annotations


class DatabaseError(RuntimeError):
    """Base error for database adapter failures."""

    @classmethod
    def read_failed(cls, cause: Exception) -> DatabaseError:
        return cls(f"Database read failed: {cause}")

    @classmethod
    def insert_failed(cls, cause: Exception) -> DatabaseError:
        return cls(f"Database insert failed: {cause}")

    @classmethod
    def write_failed(cls, cause: Exception) -> DatabaseError:
        return cls(f"Database write failed: {cause}")
    
    @classmethod
    def operation_failed(cls, cause: Exception) -> DatabaseError:
        return cls(f"Database operation failed: {cause}")

    @classmethod
    def wrong_query_result(cls) -> DatabaseError:
        return cls("Database query did not return a result set.")

    @classmethod
    def missing_returning_id(cls) -> DatabaseError:
        return cls("Database insert did not return an id. Did you forget RETURNING id?")

    @classmethod
    def invalid_returned_id_type(cls, value: object) -> DatabaseError:
        return cls(f"Database returned an invalid id value: {value!r}.")
