"""Unit tests for query-to-use-case argument adaptation."""

import unittest
from unittest.mock import MagicMock

from src.application.handlers.queries.trucks.view_all_trucks import ViewAllTrucksQueryHandler
from src.application.queries.trucks.view_all_trucks import ViewAllTrucksQuery


class QueryHandlersShould(unittest.TestCase):
    """Verify that query handlers delegate once with the intended arguments."""

    def test_view_all_trucks_delegates_without_arguments(self) -> None:
        use_case = MagicMock()
        expected = object()
        use_case.execute.return_value = expected

        result = ViewAllTrucksQueryHandler(use_case).execute(ViewAllTrucksQuery())

        self.assertIs(result, expected)
        use_case.execute.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
