"""Unit tests for query-to-use-case argument adaptation."""

import unittest
from datetime import datetime
from unittest.mock import MagicMock

from src.application.handlers.queries.routes.view_route import ViewRouteQueryHandler
from src.application.handlers.queries.routes.view_routes_in_progress import ViewRoutesInProgressQueryHandler
from src.application.handlers.queries.trucks.view_all_trucks import ViewAllTrucksQueryHandler
from src.application.queries.routes.view_route import ViewRouteQuery
from src.application.queries.routes.view_routes_in_progress import ViewRoutesInProgressQuery
from src.application.queries.trucks.view_all_trucks import ViewAllTrucksQuery

NOW = datetime(2026, 8, 6, 12, 30)


class QueryHandlersShould(unittest.TestCase):
    """Verify that query handlers delegate once with the intended arguments."""

    def test_view_route_forwards_identifier(self) -> None:
        use_case = MagicMock()
        expected = object()
        use_case.execute.return_value = expected

        result = ViewRouteQueryHandler(use_case).execute(ViewRouteQuery(route_id=6))

        self.assertIs(result, expected)
        use_case.execute.assert_called_once_with(6)

    def test_view_routes_in_progress_forwards_business_time(self) -> None:
        use_case = MagicMock()
        expected = object()
        use_case.execute.return_value = expected

        result = ViewRoutesInProgressQueryHandler(use_case).execute(ViewRoutesInProgressQuery(now=NOW))

        self.assertIs(result, expected)
        use_case.execute.assert_called_once_with(NOW)

    def test_view_all_trucks_delegates_without_arguments(self) -> None:
        use_case = MagicMock()
        expected = object()
        use_case.execute.return_value = expected

        result = ViewAllTrucksQueryHandler(use_case).execute(ViewAllTrucksQuery())

        self.assertIs(result, expected)
        use_case.execute.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
