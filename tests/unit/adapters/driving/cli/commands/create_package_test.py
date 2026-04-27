import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.adapters.driving.cli.commands.create_package import CreatePackage


class CreatePackage_Tests(unittest.TestCase):
    def make_cmd(self, params: list[str], *, authorized: bool = True) -> CreatePackage:
        cmd = CreatePackage.__new__(CreatePackage)
        cmd._params = params  # type: ignore[reportAttributeAccessIssue]
        cmd._use_case = MagicMock()  # type: ignore[reportAttributeAccessIssue]

        cmd._authz = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        cmd._authz.has.return_value = authorized  # type: ignore[reportAttributeAccessIssue]

        return cmd

    def test_mutates_state_true(self) -> None:
        self.assertTrue(CreatePackage.mutates_state)

    def test_execute_without_permission_raises(self) -> None:
        cmd = self.make_cmd(["A1", "B2", "12.5", "Alice"], authorized=False)

        with self.assertRaises(PermissionError) as ctx:
            cmd.execute()

        self.assertIn("PACKAGE_CREATE", str(ctx.exception))
        cmd._use_case.execute.assert_not_called()  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.create_package.validate_params_count")
    @patch("src.adapters.driving.cli.commands.create_package.try_parse_float")
    def test_success_minimal_required_params(
        self,
        mock_parse_float: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        mock_parse_float.side_effect = float
        cmd = self.make_cmd(["A1", "B2", "12.5", "Alice"], authorized=True)

        pkg = SimpleNamespace(package_id=123, customer=SimpleNamespace(customer_id=55))
        cmd._use_case.execute.return_value = pkg  # type: ignore[reportAttributeAccessIssue]

        result = cmd.execute()

        mock_validate.assert_called_once_with(["A1", "B2", "12.5", "Alice"], 4, 6)
        mock_parse_float.assert_called_once_with("12.5")
        cmd._use_case.execute.assert_called_once_with(  # type: ignore[reportUnknownMemberType]
            start="A1",
            end="B2",
            weight=12.5,
            name="Alice",
            email="",
            phone="",
        )
        self.assertEqual(result, "Package 123 was created for customer Alice (ID: 55) successfully.")

    @patch("src.adapters.driving.cli.commands.create_package.validate_params_count")
    @patch("src.adapters.driving.cli.commands.create_package.try_parse_float")
    def test_success_with_all_params(
        self,
        mock_parse_float: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        mock_parse_float.return_value = 7.0
        cmd = self.make_cmd(["S1", "E9", "7", "Bob", "bob@ex.com", "0412345678"], authorized=True)

        pkg = SimpleNamespace(package_id=999, customer=SimpleNamespace(customer_id=1))
        cmd._use_case.execute.return_value = pkg  # type: ignore[reportAttributeAccessIssue]

        result = cmd.execute()

        mock_validate.assert_called_once_with(["S1", "E9", "7", "Bob", "bob@ex.com", "0412345678"], 4, 6)
        mock_parse_float.assert_called_once_with("7")
        cmd._use_case.execute.assert_called_once_with(  # type: ignore[reportUnknownMemberType]
            start="S1",
            end="E9",
            weight=7.0,
            name="Bob",
            email="bob@ex.com",
            phone="0412345678",
        )
        self.assertEqual(result, "Package 999 was created for customer Bob (ID: 1) successfully.")

    @patch("src.adapters.driving.cli.commands.create_package.validate_params_count")
    @patch("src.adapters.driving.cli.commands.create_package.try_parse_float")
    def test_weight_parse_failure_propagates(
        self,
        mock_parse_float: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        mock_parse_float.side_effect = ValueError("not a number")
        cmd = self.make_cmd(["A1", "B2", "x", "Alice"], authorized=True)

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()

        self.assertIn("not a number", str(ctx.exception))
        cmd._use_case.execute.assert_not_called()  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.create_package.validate_params_count")
    @patch("src.adapters.driving.cli.commands.create_package.try_parse_float")
    def test_downstream_use_case_error_propagates(
        self,
        mock_parse_float: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        mock_parse_float.return_value = 2.5
        cmd = self.make_cmd(["A1", "B2", "2.5", "Alice"], authorized=True)
        cmd._use_case.execute.side_effect = RuntimeError("db error")  # type: ignore[reportAttributeAccessIssue]

        with self.assertRaises(RuntimeError) as ctx:
            cmd.execute()

        self.assertIn("db error", str(ctx.exception))
        cmd._use_case.execute.assert_called_once_with(  # type: ignore[reportUnknownMemberType]
            start="A1",
            end="B2",
            weight=2.5,
            name="Alice",
            email="",
            phone="",
        )

    @patch("src.adapters.driving.cli.commands.create_package.validate_params_count")
    @patch("src.adapters.driving.cli.commands.create_package.try_parse_float")
    def test_validate_called_with_min_max(
        self,
        mock_parse_float: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        mock_parse_float.return_value = 1.0
        params = ["S", "E", "1", "N"]
        cmd = self.make_cmd(params, authorized=True)
        pkg = SimpleNamespace(package_id=1, customer=SimpleNamespace(customer_id=1))
        cmd._use_case.execute.return_value = pkg  # type: ignore[reportAttributeAccessIssue]

        _ = cmd.execute()

        mock_validate.assert_called_once_with(params, 4, 6)

    @patch("src.adapters.driving.cli.commands.create_package.validate_params_count")
    @patch("src.adapters.driving.cli.commands.create_package.try_parse_float")
    def test_optional_email_phone_default_to_empty(
        self,
        mock_parse_float: MagicMock,
        mock_validate: MagicMock,
    ) -> None:
        mock_parse_float.return_value = 4.2
        cmd = self.make_cmd(["S", "E", "4.2", "Name"], authorized=True)
        pkg = SimpleNamespace(package_id=5, customer=SimpleNamespace(customer_id=6))
        cmd._use_case.execute.return_value = pkg  # type: ignore[reportAttributeAccessIssue]

        _ = cmd.execute()

        cmd._use_case.execute.assert_called_once_with(  # type: ignore[reportUnknownMemberType]
            start="S",
            end="E",
            weight=4.2,
            name="Name",
            email="",
            phone="",
        )
