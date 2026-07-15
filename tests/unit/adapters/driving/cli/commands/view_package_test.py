import unittest
from unittest.mock import MagicMock, patch

from src.adapters.driving.cli.commands.view_package import ViewPackage


class TestViewPackage_Should(unittest.TestCase):
    def make_cmd(self, params: list[str]) -> ViewPackage:
        cmd = ViewPackage.__new__(ViewPackage)
        cmd._params = params  # type: ignore[reportAttributeAccessIssue]
        cmd._use_case = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        cmd._event_collector = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        return cmd

    def test_execute_propagates_permission_errors_from_use_case(self) -> None:
        cmd = self.make_cmd(["123"])
        cmd._use_case.execute.side_effect = PermissionError("Missing permission: PACKAGE_VIEW")  # type: ignore[reportAttributeAccessIssue]

        with self.assertRaises(PermissionError) as context:
            cmd.execute()

        self.assertIn("PACKAGE_VIEW", str(context.exception))
        cmd._use_case.execute.assert_called_once_with(123)  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.view_package.validate_params_exact")
    @patch("src.adapters.driving.cli.commands.view_package.try_parse_int")
    @patch("src.adapters.driving.cli.commands.view_package.render_package_info")
    def test_successful_execution(
        self,
        mock_render: MagicMock,
        mock_try_parse: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        cmd = self.make_cmd(["123"])
        mock_try_parse.return_value = 123

        mock_package = MagicMock()
        mock_render.return_value = "Package 123 details"
        cmd._use_case.execute.return_value = mock_package  # type: ignore[reportAttributeAccessIssue]

        result = cmd.execute()

        mock_validate.assert_called_once_with(["123"], 1)
        mock_try_parse.assert_called_once_with("123", "package_id")
        cmd._use_case.execute.assert_called_once_with(123)  # type: ignore[reportUnknownMemberType]
        mock_render.assert_called_once_with(mock_package)
        self.assertEqual(result, "Package 123 details")

    @patch("src.adapters.driving.cli.commands.view_package.validate_params_exact")
    @patch("src.adapters.driving.cli.commands.view_package.try_parse_int")
    def test_package_not_found(
        self,
        mock_try_parse: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        cmd = self.make_cmd(["999"])
        mock_try_parse.return_value = 999
        cmd._use_case.execute.side_effect = ValueError("Package with ID 999 not found")  # type: ignore[reportAttributeAccessIssue]

        with self.assertRaises(ValueError) as context:
            cmd.execute()

        self.assertIn("Package with ID 999 not found", str(context.exception))
        mock_validate.assert_called_once_with(["999"], 1)
        mock_try_parse.assert_called_once_with("999", "package_id")
        cmd._use_case.execute.assert_called_once_with(999)  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.view_package.validate_params_exact")
    def test_invalid_parameter_count(self, mock_validate: MagicMock) -> None:
        cmd = self.make_cmd([])
        mock_validate.side_effect = ValueError("Expected 1 parameter(s).")

        with self.assertRaises(ValueError) as context:
            cmd.execute()

        self.assertIn("Expected 1 parameter(s).", str(context.exception))
        mock_validate.assert_called_once_with([], 1)
        cmd._use_case.execute.assert_not_called()  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.view_package.validate_params_exact")
    @patch("src.adapters.driving.cli.commands.view_package.try_parse_int")
    def test_invalid_parameter_type(
        self,
        mock_try_parse: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        cmd = self.make_cmd(["abc"])
        mock_try_parse.side_effect = ValueError("Parameter 'abc' is not a valid integer.")

        with self.assertRaises(ValueError) as context:
            cmd.execute()

        self.assertIn("Parameter 'abc' is not a valid integer.", str(context.exception))
        mock_validate.assert_called_once_with(["abc"], 1)
        mock_try_parse.assert_called_once_with("abc", "package_id")
        cmd._use_case.execute.assert_not_called()  # type: ignore[reportUnknownMemberType]
