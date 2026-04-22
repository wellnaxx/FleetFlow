from __future__ import annotations

import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from src.adapters.driving.cli.commands.find_suitable_routes_for_package import FindSuitableRoutesForPackage
from src.application.results.find_suitable_packages_for_route_result import SuitableRouteForPackage


class FindSuitableRoutesForPackage_Should(unittest.TestCase):
    def make_cmd(self, params: list[str], *, authorized: bool = True) -> FindSuitableRoutesForPackage:
        cmd = FindSuitableRoutesForPackage.__new__(FindSuitableRoutesForPackage)
        cmd._params = tuple(params)  # type: ignore[reportAttributeAccessIssue]
        cmd._use_case = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        cmd._app_data = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        cmd._app_data.authz = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        cmd._app_data.authz.has.return_value = authorized  # type: ignore[reportAttributeAccessIssue]
        cmd._auth = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        return cmd

    def test_execute_without_permission_raises(self) -> None:
        cmd = self.make_cmd(["77"], authorized=False)

        with self.assertRaises(PermissionError) as ctx:
            cmd.execute()

        self.assertIn("PACKAGE_FIND_ROUTE_FOR", str(ctx.exception))
        cmd._use_case.execute.assert_not_called()  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.find_suitable_routes_for_package.validate_params_exact")
    @patch("src.adapters.driving.cli.commands.find_suitable_routes_for_package.try_parse_int")
    def test_success_mixed_matches_formats_lines(self, mock_parse: MagicMock, mock_validate: MagicMock) -> None:
        mock_parse.return_value = 77
        cmd = self.make_cmd(["77"])
        cmd._use_case.execute.return_value = [  # type: ignore[reportAttributeAccessIssue]
            SuitableRouteForPackage(
                route_id=10,
                start_location="SYD",
                end_location="MEL",
                eta=datetime(2025, 10, 12, 6, 0),
                capacity_left=123.456,
                end_city="MEL",
            ),
            SuitableRouteForPackage(
                route_id=11,
                start_location="SYD",
                end_location="MEL",
                eta=None,
                capacity_left=None,
                end_city="MEL",
            ),
        ]
        result = cmd.execute()

        mock_validate.assert_called_once_with(("77",), 1)
        mock_parse.assert_called_once_with("77")
        cmd._use_case.execute.assert_called_once_with(77)  # type: ignore[reportUnknownMemberType]

        lines = result.splitlines()
        self.assertEqual(len(lines), 2)
        self.assertIn("Route 10: SYD -> MEL, ETA to MEL: 2025-10-12 06:00, Capacity left: 123.46kg", lines[0])
        self.assertIn("Route 11: SYD -> MEL, ETA to MEL: N/A, Capacity left: No truck", lines[1])

    @patch("src.adapters.driving.cli.commands.find_suitable_routes_for_package.validate_params_exact")
    @patch("src.adapters.driving.cli.commands.find_suitable_routes_for_package.try_parse_int")
    def test_no_matches_returns_friendly_message(self, mock_parse: MagicMock, mock_validate: MagicMock) -> None:
        mock_parse.return_value = 5
        cmd = self.make_cmd(["5"])
        cmd._use_case.execute.return_value = []  # type: ignore[reportAttributeAccessIssue]

        result = cmd.execute()

        self.assertEqual(result, "No suitable routes found.")
        cmd._use_case.execute.assert_called_once_with(5)  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.find_suitable_routes_for_package.validate_params_exact")
    @patch("src.adapters.driving.cli.commands.find_suitable_routes_for_package.try_parse_int")
    def test_use_case_error_bubbles(self, mock_parse: MagicMock, mock_validate: MagicMock) -> None:
        mock_parse.return_value = 42
        cmd = self.make_cmd(["42"])
        cmd._use_case.execute.side_effect = ValueError("Package with ID 42 not found.")  # type: ignore[reportAttributeAccessIssue]

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()

        self.assertIn("Package with ID 42 not found", str(ctx.exception))
        cmd._use_case.execute.assert_called_once_with(42)  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.find_suitable_routes_for_package.validate_params_exact")
    @patch("src.adapters.driving.cli.commands.find_suitable_routes_for_package.try_parse_int")
    def test_parse_failure_bubbles_and_stops(self, mock_parse: MagicMock, mock_validate: MagicMock) -> None:
        mock_parse.side_effect = ValueError("not an int")
        cmd = self.make_cmd(["x"])

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()

        self.assertIn("not an int", str(ctx.exception))
        cmd._use_case.execute.assert_not_called()  # type: ignore[reportUnknownMemberType]

    def test_validate_params_exact_called_with_one(self, _unused_mock: object = None) -> None:
        cmd = self.make_cmd(["123"])
        with (
            patch(
                "src.adapters.driving.cli.commands.find_suitable_routes_for_package.validate_params_exact"
            ) as mock_validate,
            patch(
                "src.adapters.driving.cli.commands.find_suitable_routes_for_package.try_parse_int",
                return_value=123,
            ),
            patch.object(cmd._use_case, "execute", return_value=[]),  # type: ignore[reportPrivateUsage]
        ):
            _ = cmd.execute()
            mock_validate.assert_called_once_with(("123",), 1)

    @patch("src.adapters.driving.cli.commands.find_suitable_routes_for_package.validate_params_exact")
    @patch("src.adapters.driving.cli.commands.find_suitable_routes_for_package.try_parse_int")
    def test_capacity_left_is_formatted_to_two_decimals(
        self, mock_parse: MagicMock, mock_validate: MagicMock
    ) -> None:
        mock_parse.return_value = 9
        cmd = self.make_cmd(["9"])
        cmd._use_case.execute.return_value = [  # type: ignore[reportAttributeAccessIssue]
            SuitableRouteForPackage(
                route_id=3,
                start_location="A",
                end_location="B",
                eta=None,
                capacity_left=1.2349,
                end_city="PER",
            )
        ]

        out = cmd.execute()
        self.assertIn("Capacity left: 1.23kg", out)
