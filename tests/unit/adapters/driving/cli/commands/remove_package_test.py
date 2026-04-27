import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.adapters.driving.cli.commands.remove_package import RemovePackage


class TestRemovePackage_Should(unittest.TestCase):
    def make_cmd(self, params: list[str], *, authorized: bool = True) -> RemovePackage:
        cmd = RemovePackage.__new__(RemovePackage)
        cmd._params = params  # type: ignore[reportAttributeAccessIssue]
        cmd._use_case = MagicMock()  # type: ignore[reportAttributeAccessIssue]

        cmd._authz = MagicMock()  # type: ignore[reportAttributeAccessIssue]

        def has_side_effect(permission):  # pyright: ignore[reportMissingParameterType, reportUnknownParameterType]
            return authorized

        cmd._authz.has.side_effect = has_side_effect  # type: ignore[reportAttributeAccessIssue]
        return cmd

    def test_execute_without_permission_raises(self) -> None:
        cmd = self.make_cmd(["42"], authorized=False)

        with self.assertRaises(PermissionError) as ctx:
            cmd.execute()

        self.assertIn("PACKAGE_REMOVE", str(ctx.exception))
        cmd._use_case.execute.assert_not_called()  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.remove_package.validate_params_exact")
    @patch("src.adapters.driving.cli.commands.remove_package.try_parse_int")
    def test_no_params_command(
        self,
        mock_try_parse: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        cmd = self.make_cmd([], authorized=True)
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
        cmd = self.make_cmd(["str"], authorized=True)
        mock_try_parse.side_effect = ValueError("Parameter 'str' is not a valid integer.")

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()

        self.assertIn("Parameter 'str' is not a valid integer.", str(ctx.exception))
        mock_validate.assert_called_once_with(["str"], 1)
        mock_try_parse.assert_called_once_with("str")
        cmd._use_case.execute.assert_not_called()  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.remove_package.validate_params_exact")
    @patch("src.adapters.driving.cli.commands.remove_package.try_parse_int")
    def test_removed_package_command(
        self,
        mock_try_parse: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        cmd = self.make_cmd(["42"], authorized=True)
        mock_try_parse.return_value = 42
        removed_pkg = SimpleNamespace(package_id=42)
        cmd._use_case.execute.return_value = removed_pkg  # type: ignore[reportAttributeAccessIssue]

        result = cmd.execute()

        self.assertEqual(result, "Package 42 removed.")
        mock_validate.assert_called_once_with(["42"], 1)
        mock_try_parse.assert_called_once_with("42")
        cmd._use_case.execute.assert_called_once_with(42)  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.remove_package.validate_params_exact")
    @patch("src.adapters.driving.cli.commands.remove_package.try_parse_int")
    def test_downstream_use_case_error_propagates(
        self,
        mock_try_parse: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        cmd = self.make_cmd(["42"], authorized=True)
        mock_try_parse.return_value = 42
        cmd._use_case.execute.side_effect = ValueError("Package with ID 42 not found")  # type: ignore[reportAttributeAccessIssue]

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()

        self.assertIn("Package with ID 42 not found", str(ctx.exception))
        mock_validate.assert_called_once_with(["42"], 1)
        mock_try_parse.assert_called_once_with("42")
        cmd._use_case.execute.assert_called_once_with(42)  # type: ignore[reportUnknownMemberType]
