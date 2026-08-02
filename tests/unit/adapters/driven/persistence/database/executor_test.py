import unittest
from unittest.mock import MagicMock, patch

from psycopg import IsolationLevel

from src.adapters.driven.persistence.database.errors import DatabaseError
from src.adapters.driven.persistence.database.executor import execute_returning_one, transaction_cursor

MODULE = "src.adapters.driven.persistence.database.executor"


class ExecutorShould(unittest.TestCase):
    @patch(f"{MODULE}.get_connection")
    def test_transaction_cursor_commits_on_success(
        self,
        get_connection_mock: MagicMock,
    ) -> None:
        conn, cursor = self._connection_and_cursor(get_connection_mock)

        with transaction_cursor() as yielded:
            self.assertIs(yielded, cursor)

        conn.commit.assert_called_once_with()
        conn.rollback.assert_not_called()

    @patch(f"{MODULE}.get_connection")
    def test_transaction_cursor_rolls_back_on_error(
        self,
        get_connection_mock: MagicMock,
    ) -> None:
        conn, _ = self._connection_and_cursor(get_connection_mock)

        with self.assertRaises(RuntimeError), transaction_cursor():
            raise RuntimeError("boom")

        conn.rollback.assert_called_once_with()
        conn.commit.assert_not_called()

    @patch(f"{MODULE}.get_connection")
    def test_transaction_cursor_applies_requested_characteristics_before_use(
        self,
        get_connection_mock: MagicMock,
    ) -> None:
        """Apply isolation and read-only settings to the opened connection."""
        conn, cursor = self._connection_and_cursor(get_connection_mock)

        with transaction_cursor(
            isolation_level=IsolationLevel.REPEATABLE_READ,
            read_only=True,
        ) as yielded:
            self.assertIs(yielded, cursor)
            self.assertEqual(conn.isolation_level, IsolationLevel.REPEATABLE_READ)
            self.assertIs(conn.read_only, True)

        conn.commit.assert_called_once_with()

    @patch(f"{MODULE}.get_connection")
    def test_transaction_cursor_wraps_configuration_failure(
        self,
        get_connection_mock: MagicMock,
    ) -> None:
        """Translate connection configuration errors into DatabaseError."""
        conn, _ = self._connection_and_cursor(get_connection_mock)
        type(conn).isolation_level = property(fset=MagicMock(side_effect=RuntimeError("configuration failed")))

        with (
            self.assertRaisesRegex(DatabaseError, "configuration failed"),
            transaction_cursor(isolation_level=IsolationLevel.REPEATABLE_READ),
        ):
            self.fail("Cursor should not be yielded after configuration failure.")

        conn.commit.assert_not_called()
        conn.rollback.assert_not_called()

    @patch(f"{MODULE}.get_connection")
    def test_execute_returning_one_returns_row_and_commits(
        self,
        get_connection_mock: MagicMock,
    ) -> None:
        conn, cursor = self._connection_and_cursor(get_connection_mock)
        cursor.description = [SimpleColumn("user_id"), SimpleColumn("token_version")]
        cursor.fetchone.return_value = (1, 2)

        row = execute_returning_one("UPDATE users SET token_version = token_version + 1 RETURNING *", (1,))

        self.assertEqual(row, {"user_id": 1, "token_version": 2})
        cursor.execute.assert_called_once_with(
            "UPDATE users SET token_version = token_version + 1 RETURNING *",
            (1,),
        )
        conn.commit.assert_called_once_with()

    def _connection_and_cursor(
        self,
        get_connection_mock: MagicMock,
    ) -> tuple[MagicMock, MagicMock]:
        conn = MagicMock()
        cursor = MagicMock()

        get_connection_mock.return_value.__enter__.return_value = conn
        conn.cursor.return_value.__enter__.return_value = cursor

        return conn, cursor


class SimpleColumn:
    def __init__(self, name: str) -> None:
        self.name = name
