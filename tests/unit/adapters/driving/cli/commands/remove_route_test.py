import unittest
from unittest.mock import MagicMock, patch

from src.adapters.driving.cli.commands.remove_route import RemoveRoute


class TestRemoveRoute_Should(unittest.TestCase):
    def make_cmd(self, params: list[str]) -> RemoveRoute:
        cmd = RemoveRoute.__new__(RemoveRoute)
        cmd._params = tuple(params)  # type: ignore[reportAttributeAccessIssue]
        cmd._use_case = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        return cmd

    def test_execute_propagates_permission_errors_from_use_case(self) -> None:
        cmd = self.make_cmd(["42"])
        cmd._use_case.execute.side_effect = PermissionError("Missing permission: ROUTE_REMOVE")  # type: ignore[reportAttributeAccessIssue]

        with self.assertRaises(PermissionError) as ctx:
            cmd.execute()

        self.assertIn("ROUTE_REMOVE", str(ctx.exception))
        cmd._use_case.execute.assert_called_once_with(42)  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.remove_route.validate_params_exact")
    @patch("src.adapters.driving.cli.commands.remove_route.try_parse_int")
    def test_no_params_command(
        self,
        mock_parse: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        cmd = self.make_cmd([])
        mock_validate.side_effect = ValueError("Expected 1 parameter(s).")

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()

        self.assertIn("Expected 1 parameter(s).", str(ctx.exception))
        mock_validate.assert_called_once_with((), 1)
        mock_parse.assert_not_called()
        cmd._use_case.execute.assert_not_called()  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.remove_route.validate_params_exact")
    @patch("src.adapters.driving.cli.commands.remove_route.try_parse_int")
    def test_str_params_command(
        self,
        mock_parse: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        cmd = self.make_cmd(["str"])
        mock_parse.side_effect = ValueError("Parameter 'str' is not a valid integer.")

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()

        self.assertIn("Parameter 'str' is not a valid integer.", str(ctx.exception))
        mock_validate.assert_called_once_with(("str",), 1)
        mock_parse.assert_called_once_with("str")
        cmd._use_case.execute.assert_not_called()  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.remove_route.validate_params_exact")
    @patch("src.adapters.driving.cli.commands.remove_route.try_parse_int")
    def test_removed_route_command(
        self,
        mock_parse: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        cmd = self.make_cmd(["42"])
        mock_parse.return_value = 42

        route = MagicMock()
        route.route_id = 42
        cmd._use_case.execute.return_value = route  # type: ignore[reportAttributeAccessIssue]

        result = cmd.execute()

        self.assertEqual(result, "Route 42 removed.")
        mock_validate.assert_called_once_with(("42",), 1)
        mock_parse.assert_called_once_with("42")
        cmd._use_case.execute.assert_called_once_with(42)  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.remove_route.validate_params_exact")
    @patch("src.adapters.driving.cli.commands.remove_route.try_parse_int")
    def test_downstream_use_case_error_propagates(
        self,
        mock_parse: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        cmd = self.make_cmd(["42"])
        mock_parse.return_value = 42
        cmd._use_case.execute.side_effect = ValueError("Route with ID 42 not found")  # type: ignore[reportAttributeAccessIssue]

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()

        self.assertIn("Route with ID 42 not found", str(ctx.exception))
        mock_validate.assert_called_once_with(("42",), 1)
        mock_parse.assert_called_once_with("42")
        cmd._use_case.execute.assert_called_once_with(42)  # type: ignore[reportUnknownMemberType]
