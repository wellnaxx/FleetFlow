import unittest
from unittest.mock import MagicMock, patch

from src.adapters.driven.persistence.database.executor import transaction_cursor

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

    def _connection_and_cursor(
        self,
        get_connection_mock: MagicMock,
    ) -> tuple[MagicMock, MagicMock]:
        conn = MagicMock()
        cursor = MagicMock()

        get_connection_mock.return_value.__enter__.return_value = conn
        conn.cursor.return_value.__enter__.return_value = cursor

        return conn, cursor
