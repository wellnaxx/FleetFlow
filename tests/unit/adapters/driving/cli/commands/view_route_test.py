import unittest
from unittest.mock import MagicMock, patch

from src.adapters.driving.cli.commands.view_route import ViewRoute


class ViewRoute_Should(unittest.TestCase):
    def make_cmd(self, params: list[str], *, authorized: bool = True) -> ViewRoute:
        cmd = ViewRoute.__new__(ViewRoute)
        cmd._params = tuple(params)  # type: ignore[reportAttributeAccessIssue]
        cmd._use_case = MagicMock()  # type: ignore[reportAttributeAccessIssue]

        cmd._authz = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        cmd._authz.has.return_value = authorized  # type: ignore[reportAttributeAccessIssue]

        cmd._auth = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        return cmd

    def test_execute_without_permission_raises(self) -> None:
        cmd = self.make_cmd(["12"], authorized=False)

        with self.assertRaises(PermissionError) as ctx:
            cmd.execute()

        self.assertIn("ROUTE_VIEW", str(ctx.exception))
        cmd._use_case.execute.assert_not_called()  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.view_route.validate_params_exact")
    @patch("src.adapters.driving.cli.commands.view_route.try_parse_int")
    def test_success_returns_route_info(self, mock_parse: MagicMock, mock_validate: MagicMock) -> None:
        mock_parse.return_value = 12
        cmd = self.make_cmd(["12"], authorized=True)

        route = MagicMock()
        route.info.return_value = "ROUTE-INFO"
        cmd._use_case.execute.return_value = route  # type: ignore[reportAttributeAccessIssue]

        result = cmd.execute()

        mock_validate.assert_called_once_with(("12",), 1)
        mock_parse.assert_called_once_with("12")
        cmd._use_case.execute.assert_called_once_with(12)  # type: ignore[reportUnknownMemberType]
        route.info.assert_called_once_with()  # type: ignore[reportUnknownMemberType]
        self.assertEqual(result, "ROUTE-INFO")

    @patch("src.adapters.driving.cli.commands.view_route.validate_params_exact")
    @patch("src.adapters.driving.cli.commands.view_route.try_parse_int")
    def test_missing_route_raises(self, mock_parse: MagicMock, mock_validate: MagicMock) -> None:
        mock_parse.return_value = 77
        cmd = self.make_cmd(["77"], authorized=True)
        cmd._use_case.execute.side_effect = ValueError("Route with ID 77 not found")  # type: ignore[reportAttributeAccessIssue]

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()

        self.assertIn("Route with ID 77 not found", str(ctx.exception))
        mock_validate.assert_called_once_with(("77",), 1)
        mock_parse.assert_called_once_with("77")
        cmd._use_case.execute.assert_called_once_with(77)  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.view_route.validate_params_exact")
    @patch("src.adapters.driving.cli.commands.view_route.try_parse_int")
    def test_parse_failure_bubbles_and_stops(self, mock_parse: MagicMock, mock_validate: MagicMock) -> None:
        mock_parse.side_effect = ValueError("not an int")
        cmd = self.make_cmd(["abc"], authorized=True)

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()

        self.assertIn("not an int", str(ctx.exception))
        mock_validate.assert_called_once_with(("abc",), 1)
        mock_parse.assert_called_once_with("abc")
        cmd._use_case.execute.assert_not_called()  # type: ignore[reportUnknownMemberType]

    def test_validate_params_exact_called_with_one(self) -> None:
        cmd = self.make_cmd(["5"], authorized=True)

        with (
            patch("src.adapters.driving.cli.commands.view_route.validate_params_exact") as mock_validate,
            patch("src.adapters.driving.cli.commands.view_route.try_parse_int", return_value=5),
        ):
            route = MagicMock()
            route.info.return_value = "ok"
            cmd._use_case.execute.return_value = route  # type: ignore[reportAttributeAccessIssue]

            _ = cmd.execute()

            mock_validate.assert_called_once_with(("5",), 1)

    @patch("src.adapters.driving.cli.commands.view_route.validate_params_exact")
    @patch("src.adapters.driving.cli.commands.view_route.try_parse_int")
    def test_ignores_extra_params_beyond_first(self, mock_parse: MagicMock, mock_validate: MagicMock) -> None:
        mock_parse.return_value = 1
        cmd = self.make_cmd(["1", "extra", "ignored"], authorized=True)

        route = MagicMock()
        route.info.return_value = "ok"
        cmd._use_case.execute.return_value = route  # type: ignore[reportAttributeAccessIssue]

        _ = cmd.execute()

        mock_validate.assert_called_once_with(("1", "extra", "ignored"), 1)
        mock_parse.assert_called_once_with("1")
        cmd._use_case.execute.assert_called_once_with(1)  # type: ignore[reportUnknownMemberType]

    def test_no_mutates_flags(self) -> None:
        self.assertFalse(getattr(ViewRoute, "mutates_state", False))
        self.assertFalse(getattr(ViewRoute, "mutates_session", False))
