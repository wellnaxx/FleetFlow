import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.adapters.driving.cli.commands.remove_package import RemovePackage


class TestRemovePackage_Should(unittest.TestCase):
    def make_cmd(self, params: list[str]) -> RemovePackage:
        cmd = RemovePackage.__new__(RemovePackage)
        cmd._params = params  # type: ignore[reportAttributeAccessIssue]
        cmd._use_case = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        cmd._event_collector = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        return cmd

    def test_execute_propagates_permission_errors_from_use_case(self) -> None:
        cmd = self.make_cmd(["42"])
        cmd._use_case.execute.side_effect = PermissionError("Missing permission: PACKAGE_REMOVE")  # type: ignore[reportAttributeAccessIssue]

        with self.assertRaises(PermissionError) as ctx:
            cmd.execute()

        self.assertIn("PACKAGE_REMOVE", str(ctx.exception))
        cmd._use_case.execute.assert_called_once_with(42)  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.remove_package.validate_params_exact")
    @patch("src.adapters.driving.cli.commands.remove_package.try_parse_int")
    def test_no_params_command(
        self,
        mock_try_parse: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        cmd = self.make_cmd([])
        mock_validate.side_effect = ValueError("Expected 1 parameter(s).")

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()

        self.assertIn("Expected 1 parameter(s).", str(ctx.exception))
        mock_validate.assert_called_once_with([], 1)
        mock_try_parse.assert_not_called()
        cmd._use_case.execute.assert_not_called()  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.remove_package.validate_params_exact")
    @patch("src.adapters.driving.cli.commands.remove_package.try_parse_int")
    def test_str_params_command(
        self,
        mock_try_parse: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        cmd = self.make_cmd(["str"])
        mock_try_parse.side_effect = ValueError("Parameter 'str' is not a valid integer.")

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()

        self.assertIn("Parameter 'str' is not a valid integer.", str(ctx.exception))
        mock_validate.assert_called_once_with(["str"], 1)
        mock_try_parse.assert_called_once_with("str", "package_id")
        cmd._use_case.execute.assert_not_called()  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.remove_package.validate_params_exact")
    @patch("src.adapters.driving.cli.commands.remove_package.try_parse_int")
    def test_removed_package_command(
        self,
        mock_try_parse: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        cmd = self.make_cmd(["42"])
        mock_try_parse.return_value = 42
        package = SimpleNamespace(package_id=42)
        customer = MagicMock()
        route = MagicMock()
        cmd._use_case.execute.return_value = SimpleNamespace(  # type: ignore[reportAttributeAccessIssue]
            package=package,
            customer=customer,
            route=route,
        )

        result = cmd.execute()

        self.assertEqual(result, "Package 42 removed.")
        mock_validate.assert_called_once_with(["42"], 1)
        mock_try_parse.assert_called_once_with("42", "package_id")
        cmd._use_case.execute.assert_called_once_with(42)  # type: ignore[reportUnknownMemberType]
        cmd._event_collector.drain.assert_called_once_with((package, customer, route))  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.remove_package.validate_params_exact")
    @patch("src.adapters.driving.cli.commands.remove_package.try_parse_int")
    def test_removed_package_without_route_drains_package_and_customer_only(
        self,
        mock_try_parse: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        cmd = self.make_cmd(["42"])
        mock_try_parse.return_value = 42
        package = SimpleNamespace(package_id=42)
        customer = MagicMock()
        cmd._use_case.execute.return_value = SimpleNamespace(  # type: ignore[reportAttributeAccessIssue]
            package=package,
            customer=customer,
            route=None,
        )

        result = cmd.execute()

        self.assertEqual(result, "Package 42 removed.")
        mock_validate.assert_called_once_with(["42"], 1)
        mock_try_parse.assert_called_once_with("42", "package_id")
        cmd._use_case.execute.assert_called_once_with(42)  # type: ignore[reportUnknownMemberType]
        cmd._event_collector.drain.assert_called_once_with((package, customer))  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.remove_package.validate_params_exact")
    @patch("src.adapters.driving.cli.commands.remove_package.try_parse_int")
    def test_downstream_use_case_error_propagates(
        self,
        mock_try_parse: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        cmd = self.make_cmd(["42"])
        mock_try_parse.return_value = 42
        cmd._use_case.execute.side_effect = ValueError("Package with ID 42 not found")  # type: ignore[reportAttributeAccessIssue]

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()

        self.assertIn("Package with ID 42 not found", str(ctx.exception))
        mock_validate.assert_called_once_with(["42"], 1)
        mock_try_parse.assert_called_once_with("42", "package_id")
        cmd._use_case.execute.assert_called_once_with(42)  # type: ignore[reportUnknownMemberType]
