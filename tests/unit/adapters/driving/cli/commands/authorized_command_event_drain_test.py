"""Cross-command tests for authorized CLI event drainage."""

import unittest
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, patch

from src.adapters.driving.cli.commands.find_suitable_routes_for_package import (
    FindSuitableRoutesForPackage,
)
from src.adapters.driving.cli.commands.find_suitable_trucks_for_route import (
    FindSuitableTrucksForRoute,
)
from src.adapters.driving.cli.commands.remove_route import RemoveRoute
from src.adapters.driving.cli.commands.view_all_packages import ViewAllPackages
from src.adapters.driving.cli.commands.view_all_routes import ViewAllRoutes
from src.adapters.driving.cli.commands.view_all_trucks import ViewAllTrucks
from src.adapters.driving.cli.commands.view_package import ViewPackage
from src.adapters.driving.cli.commands.view_route import ViewRoute
from src.adapters.driving.cli.commands.view_routes_in_progress import ViewRoutesInProgress
from src.adapters.driving.cli.commands.view_unassigned_packages import ViewUnassignedPackages
from src.application.use_cases.pagination import PageResult


class AuthorizedCommandEventDrainShould(unittest.TestCase):
    """Verify authorized commands drain their use-case recorder."""

    def test_drain_read_and_search_use_cases_after_success(self) -> None:
        page = PageResult[object](items=(), total=None, limit=None, offset=0)
        cases: tuple[tuple[type[Any], tuple[str, ...], object], ...] = (
            (ViewAllPackages, (), page),
            (ViewUnassignedPackages, (), page),
            (ViewAllRoutes, (), page),
            (ViewAllTrucks, (), list[object]()),
            (ViewRoutesInProgress, (), list[object]()),
            (FindSuitableRoutesForPackage, ("1",), list[object]()),
            (FindSuitableTrucksForRoute, ("1",), list[object]()),
        )

        for command_type, params, result in cases:
            with self.subTest(command=command_type.__name__):
                use_case = MagicMock()
                collector = MagicMock()
                use_case.execute.return_value = result
                command = command_type(params, use_case, collector)

                with patch(
                    "src.adapters.driving.cli.commands.view_routes_in_progress.datetime"
                ) as datetime_mock:
                    datetime_mock.now.return_value = datetime(2026, 7, 12, 12, 0)
                    command.execute()

                collector.drain.assert_called_once_with((use_case,))

    def test_drain_single_entity_view_use_cases_after_success(self) -> None:
        package = MagicMock()
        route = MagicMock()
        cases = (
            (ViewPackage, ("1",), package),
            (ViewRoute, ("1",), route),
        )

        for command_type, params, result in cases:
            with self.subTest(command=command_type.__name__):
                use_case = MagicMock()
                collector = MagicMock()
                use_case.execute.return_value = result
                command = command_type(params, use_case, collector)

                with (
                    patch(
                        "src.adapters.driving.cli.commands.view_package.render_package_info",
                        return_value="package",
                    ),
                    patch(
                        "src.adapters.driving.cli.commands.view_route.render_route_info",
                        return_value="route",
                    ),
                ):
                    command.execute()

                collector.drain.assert_called_once_with((use_case,))

    def test_best_effort_drain_authorization_denials(self) -> None:
        for command_type, params in (
            (ViewPackage, ("1",)),
            (FindSuitableTrucksForRoute, ("1",)),
            (RemoveRoute, ("1",)),
        ):
            with self.subTest(command=command_type.__name__):
                use_case = MagicMock()
                collector = MagicMock()
                use_case.execute.side_effect = PermissionError("Forbidden")
                command = command_type(params, use_case, collector)

                with self.assertRaises(PermissionError):
                    command.execute()

                collector.drain.assert_called_once_with((use_case,))


if __name__ == "__main__":
    unittest.main()
