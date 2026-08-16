"""Unit tests for query-to-use-case argument adaptation."""

import unittest
from datetime import datetime
from unittest.mock import MagicMock

from src.application.handlers.queries.audit.view_audits import ViewAuditsQueryHandler
from src.application.handlers.queries.customers.view_all_customers import ViewAllCustomersQueryHandler
from src.application.handlers.queries.fleet.get_fleet_overview import GetFleetOverviewQueryHandler
from src.application.handlers.queries.packages.view_all_packages import ViewAllPackagesQueryHandler
from src.application.handlers.queries.packages.view_package import ViewPackageQueryHandler
from src.application.handlers.queries.packages.view_unassigned_packages import (
    ViewUnassignedPackagesQueryHandler,
)
from src.application.handlers.queries.routes.find_suitable_routes_for_package import (
    FindSuitableRoutesForPackageQueryHandler,
)
from src.application.handlers.queries.routes.find_suitable_trucks_for_route import (
    FindSuitableTrucksForRouteQueryHandler,
)
from src.application.handlers.queries.routes.view_all_routes import ViewAllRoutesQueryHandler
from src.application.handlers.queries.routes.view_route import ViewRouteQueryHandler
from src.application.handlers.queries.routes.view_routes_in_progress import ViewRoutesInProgressQueryHandler
from src.application.handlers.queries.trucks.view_all_trucks import ViewAllTrucksQueryHandler
from src.application.models.audit_log_query import AuditLogFilter, AuditLogQuery
from src.application.queries.customers.view_all_customers import ViewAllCustomersQuery
from src.application.queries.fleet.get_fleet_overview import GetFleetOverviewQuery
from src.application.queries.packages.view_all_packages import ViewAllPackagesQuery
from src.application.queries.packages.view_package import ViewPackageQuery
from src.application.queries.packages.view_unassigned_packages import ViewUnassignedPackagesQuery
from src.application.queries.routes.find_suitable_routes_for_package import FindSuitableRoutesForPackageQuery
from src.application.queries.routes.find_suitable_trucks_for_route import FindSuitableTrucksForRouteQuery
from src.application.queries.routes.view_all_routes import ViewAllRoutesQuery
from src.application.queries.routes.view_route import ViewRouteQuery
from src.application.queries.routes.view_routes_in_progress import ViewRoutesInProgressQuery
from src.application.queries.trucks.view_all_trucks import ViewAllTrucksQuery
from src.application.use_cases.pagination import PageQuery

NOW = datetime(2026, 8, 6, 12, 30)


class QueryHandlersShould(unittest.TestCase):
    """Verify that query handlers delegate once with the intended arguments."""

    def test_view_audits_forwards_canonical_query_unchanged(self) -> None:
        use_case = MagicMock()
        expected = object()
        use_case.execute.return_value = expected
        query = AuditLogQuery(
            page=PageQuery(limit=25, offset=50, include_total=True),
            filters=AuditLogFilter(event_type="PackageCreated"),
        )

        result = ViewAuditsQueryHandler(use_case).execute(query)

        self.assertIs(result, expected)
        use_case.execute.assert_called_once_with(query)

    def test_view_all_customers_forwards_page(self) -> None:
        use_case = MagicMock()
        expected = object()
        use_case.execute.return_value = expected
        page = PageQuery(limit=12, offset=24, include_total=True)

        result = ViewAllCustomersQueryHandler(use_case).execute(ViewAllCustomersQuery(page=page))

        self.assertIs(result, expected)
        use_case.execute.assert_called_once_with(page)

    def test_view_all_packages_forwards_page(self) -> None:
        use_case = MagicMock()
        expected = object()
        use_case.execute.return_value = expected
        page = PageQuery(limit=12, offset=24, include_total=True)

        result = ViewAllPackagesQueryHandler(use_case).execute(ViewAllPackagesQuery(page=page))

        self.assertIs(result, expected)
        use_case.execute.assert_called_once_with(page)

    def test_view_unassigned_packages_forwards_page(self) -> None:
        use_case = MagicMock()
        expected = object()
        use_case.execute.return_value = expected
        page = PageQuery(limit=12, offset=24, include_total=True)

        result = ViewUnassignedPackagesQueryHandler(use_case).execute(ViewUnassignedPackagesQuery(page=page))

        self.assertIs(result, expected)
        use_case.execute.assert_called_once_with(page)

    def test_view_all_routes_forwards_page(self) -> None:
        use_case = MagicMock()
        expected = object()
        use_case.execute.return_value = expected
        page = PageQuery(limit=12, offset=24, include_total=True)

        result = ViewAllRoutesQueryHandler(use_case).execute(ViewAllRoutesQuery(page=page))

        self.assertIs(result, expected)
        use_case.execute.assert_called_once_with(page)

    def test_get_fleet_overview_forwards_active_route_limit(self) -> None:
        use_case = MagicMock()
        expected = object()
        use_case.execute.return_value = expected

        result = GetFleetOverviewQueryHandler(use_case).execute(GetFleetOverviewQuery(active_route_limit=25))

        self.assertIs(result, expected)
        use_case.execute.assert_called_once_with(25)

    def test_view_package_forwards_identifier(self) -> None:
        use_case = MagicMock()
        expected = object()
        use_case.execute.return_value = expected

        result = ViewPackageQueryHandler(use_case).execute(ViewPackageQuery(package_id=4))

        self.assertIs(result, expected)
        use_case.execute.assert_called_once_with(4)

    def test_find_suitable_routes_forwards_package_identifier(self) -> None:
        use_case = MagicMock()
        expected = object()
        use_case.execute.return_value = expected

        result = FindSuitableRoutesForPackageQueryHandler(use_case).execute(
            FindSuitableRoutesForPackageQuery(package_id=4)
        )

        self.assertIs(result, expected)
        use_case.execute.assert_called_once_with(4)

    def test_find_suitable_trucks_forwards_route_identifier(self) -> None:
        use_case = MagicMock()
        expected = object()
        use_case.execute.return_value = expected

        result = FindSuitableTrucksForRouteQueryHandler(use_case).execute(
            FindSuitableTrucksForRouteQuery(route_id=6)
        )

        self.assertIs(result, expected)
        use_case.execute.assert_called_once_with(6)

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
