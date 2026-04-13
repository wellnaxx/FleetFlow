import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

from src.commands.create_package import CreatePackage


class CreatePackage_Tests(unittest.TestCase):
    def make_cmd(self, params: list[str]) -> CreatePackage:
        cmd = CreatePackage.__new__(CreatePackage)
        cmd._params = params  # type: ignore[reportAttributeAccessIssue]
        cmd._app_data = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        return cmd

    def test_mutates_state_true(self) -> None:
        self.assertTrue(CreatePackage.mutates_state)

    @patch("src.commands.create_package.Map.is_valid_location", return_value=True)
    @patch("src.commands.create_package.validate_params_count")
    @patch("src.commands.create_package.try_parse_float")
    def test_success_minimal_required_params(
        self, mock_parse_float: MagicMock, mock_validate: MagicMock, mock_is_valid: MagicMock
    ) -> None:
        # Arrange
        mock_parse_float.side_effect = float
        cmd = self.make_cmd(["A1", "B2", "12.5", "Alice"])
        # stub return record
        pkg = SimpleNamespace(package_id=123, customer=SimpleNamespace(customer_id=55))
        cmd._app_data.create_package.return_value = pkg  # type: ignore[reportAttributeAccessIssue]

        # Act
        result = cmd.execute()

        # Assert
        mock_validate.assert_called_once_with(["A1", "B2", "12.5", "Alice"], 4, 6)
        self.assertEqual(mock_is_valid.call_args_list, [call("A1"), call("B2")])
        mock_parse_float.assert_called_once_with("12.5")
        cmd._app_data.create_package.assert_called_once_with("A1", "B2", 12.5, "Alice", "", "")  # type: ignore[reportUnknownMemberType]
        self.assertEqual(result, "Package 123 was created for customer Alice (ID: 55) successfully.")

    @patch("src.commands.create_package.Map.is_valid_location", return_value=True)
    @patch("src.commands.create_package.validate_params_count")
    @patch("src.commands.create_package.try_parse_float")
    def test_success_with_all_params(
        self, mock_parse_float: MagicMock, mock_validate: MagicMock, mock_is_valid: MagicMock
    ) -> None:
        mock_parse_float.return_value = 7.0
        cmd = self.make_cmd(["S1", "E9", "7", "Bob", "bob@ex.com", "0412345678"])
        pkg = SimpleNamespace(package_id=999, customer=SimpleNamespace(customer_id=1))
        cmd._app_data.create_package.return_value = pkg  # type: ignore[reportAttributeAccessIssue]

        result = cmd.execute()

        mock_validate.assert_called_once_with(["S1", "E9", "7", "Bob", "bob@ex.com", "0412345678"], 4, 6)
        self.assertEqual(mock_is_valid.call_args_list, [call("S1"), call("E9")])
        mock_parse_float.assert_called_once_with("7")
        cmd._app_data.create_package.assert_called_once_with("S1", "E9", 7.0, "Bob", "bob@ex.com", "0412345678")  # type: ignore[reportUnknownMemberType]
        self.assertEqual(result, "Package 999 was created for customer Bob (ID: 1) successfully.")

    @patch("src.commands.create_package.Map.is_valid_location")
    @patch("src.commands.create_package.validate_params_count")
    def test_invalid_start_location_raises(self, mock_validate: MagicMock, mock_is_valid: MagicMock) -> None:
        # First call (start) -> False
        mock_is_valid.side_effect = [False, True]
        cmd = self.make_cmd(["badStart", "B2", "3.14", "Alice"])

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()

        self.assertIn("Invalid start location: badStart", str(ctx.exception))
        # ensure nothing else gets called
        self.assertFalse(
            hasattr(cmd._app_data.create_package, "called") and cmd._app_data.create_package.called  # type: ignore[reportAttributeAccessIssue]
        )

    @patch("src.commands.create_package.Map.is_valid_location", return_value=True)
    @patch("src.commands.create_package.validate_params_count")
    @patch("src.commands.create_package.try_parse_float")
    def test_weight_parse_failure_propagates(
        self, mock_parse_float: MagicMock, mock_validate: MagicMock, mock_is_valid: MagicMock
    ) -> None:
        mock_parse_float.side_effect = ValueError("not a number")
        cmd = self.make_cmd(["A1", "B2", "x", "Alice"])

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()

        self.assertIn("not a number", str(ctx.exception))
        cmd._app_data.create_package.assert_not_called()  # type: ignore[reportUnknownMemberType]

    @patch("src.commands.create_package.Map.is_valid_location", return_value=True)
    @patch("src.commands.create_package.validate_params_count")
    @patch("src.commands.create_package.try_parse_float")
    def test_downstream_create_package_error_propagates(
        self, mock_parse_float: MagicMock, mock_validate: MagicMock, mock_is_valid: MagicMock
    ) -> None:
        mock_parse_float.return_value = 2.5
        cmd = self.make_cmd(["A1", "B2", "2.5", "Alice"])
        cmd._app_data.create_package.side_effect = RuntimeError("db error")  # type: ignore[reportAttributeAccessIssue]

        with self.assertRaises(RuntimeError) as ctx:
            cmd.execute()

        self.assertIn("db error", str(ctx.exception))
        cmd._app_data.create_package.assert_called_once_with("A1", "B2", 2.5, "Alice", "", "")  # type: ignore[reportUnknownMemberType]

    @patch("src.commands.create_package.Map.is_valid_location", return_value=True)
    @patch("src.commands.create_package.validate_params_count")
    @patch("src.commands.create_package.try_parse_float")
    def test_validate_called_with_min_max(
        self, mock_parse_float: MagicMock, mock_validate: MagicMock, mock_is_valid: MagicMock
    ) -> None:
        mock_parse_float.return_value = 1.0
        params = ["S", "E", "1", "N"]
        cmd = self.make_cmd(params)

        _ = cmd.execute()

        mock_validate.assert_called_once_with(params, 4, 6)

    @patch("src.commands.create_package.Map.is_valid_location", return_value=True)
    @patch("src.commands.create_package.validate_params_count")
    @patch("src.commands.create_package.try_parse_float")
    def test_optional_email_phone_default_to_empty(
        self, mock_parse_float: MagicMock, mock_validate: MagicMock, mock_is_valid: MagicMock
    ) -> None:
        mock_parse_float.return_value = 4.2
        cmd = self.make_cmd(["S", "E", "4.2", "Name"])
        pkg = SimpleNamespace(package_id=5, customer=SimpleNamespace(customer_id=6))
        cmd._app_data.create_package.return_value = pkg  # type: ignore[reportAttributeAccessIssue]

        _ = cmd.execute()

        cmd._app_data.create_package.assert_called_once_with("S", "E", 4.2, "Name", "", "")  # type: ignore[reportUnknownMemberType]
