"""Tests for lazy PostgreSQL query registration."""

import unittest
from unittest.mock import MagicMock, call, patch

from src.adapters.driven.persistence.database.queries import QueryRegistry

MODULE = "src.adapters.driven.persistence.database.queries"


def _sql_for(path: str) -> str:
    """Return identifiable SQL text for one registry path."""
    return f"SQL:{path}"


class QueryRegistryShould(unittest.TestCase):
    """Validate fleet-overview SQL loading and cached access."""

    @patch(f"{MODULE}.load_sql", side_effect=_sql_for)
    def test_loads_and_caches_all_fleet_overview_queries(
        self,
        load_sql_mock: MagicMock,
    ) -> None:
        """Load each fleet-overview file once and expose it by purpose."""
        registry = QueryRegistry()

        first = registry.fleet_overview
        second = registry.fleet_overview

        self.assertIs(first, second)
        self.assertEqual(
            (
                first.active_route_packages,
                first.active_routes,
                first.package_counts,
                first.route_counts,
                first.truck_counts,
            ),
            (
                "SQL:fleet_overview/active_route_packages.sql",
                "SQL:fleet_overview/active_routes.sql",
                "SQL:fleet_overview/package_counts.sql",
                "SQL:fleet_overview/route_counts.sql",
                "SQL:fleet_overview/truck_counts.sql",
            ),
        )
        self.assertEqual(
            load_sql_mock.call_args_list,
            [
                call("fleet_overview/active_route_packages.sql"),
                call("fleet_overview/active_routes.sql"),
                call("fleet_overview/package_counts.sql"),
                call("fleet_overview/route_counts.sql"),
                call("fleet_overview/truck_counts.sql"),
            ],
        )
