"""Cross-command tests for authorized CLI event drainage."""

import unittest
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, patch

from src.adapters.driving.cli.commands.view_all_trucks import ViewAllTrucks
from src.adapters.driving.cli.commands.view_route import ViewRoute
from src.adapters.driving.cli.commands.view_routes_in_progress import ViewRoutesInProgress


class AuthorizedCommandEventDrainShould(unittest.TestCase):
    """Verify authorized commands drain their use-case recorder."""

    def test_drain_read_and_search_use_cases_after_success(self) -> None:
        cases: tuple[tuple[type[Any], tuple[str, ...], object], ...] = (
            (ViewAllTrucks, (), list[object]()),
            (ViewRoutesInProgress, (), list[object]()),
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
        route = MagicMock()
        cases = ((ViewRoute, ("1",), route),)

        for command_type, params, result in cases:
            with self.subTest(command=command_type.__name__):
                use_case = MagicMock()
                collector = MagicMock()
                use_case.execute.return_value = result
                command = command_type(params, use_case, collector)

                with patch(
                    "src.adapters.driving.cli.commands.view_route.render_route_info",
                    return_value="route",
                ):
                    command.execute()

                collector.drain.assert_called_once_with((use_case,))


if __name__ == "__main__":
    unittest.main()
